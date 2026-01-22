"""
法规相关业务逻辑
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.models import LawCreate
from motor.motor_asyncio import AsyncIOMotorDatabase
from pathlib import Path
import json
from app.services.search_engine import get_search_engine
import hashlib
import re
import math


# 法律权重配置（权重越大排序越靠前）
LAW_WEIGHT_CONFIG = {
    "治安管理处罚法": 100,
    "中华人民共和国治安管理处罚法": 100,
    "刑法": 95,
    "中华人民共和国刑法": 95,
    "刑事诉讼法": 90,
    "中华人民共和国刑事诉讼法": 90,
    "公安机关办理行政案件程序规定": 85,
    "公安机关办理刑事案件程序规定": 80,
}
DEFAULT_WEIGHT = 50


COMMON_LAW_PREFIXES = [
    "中华人民共和国",
    "中华人民",
    "全国人民代表大会",
    "最高人民法院",
    "最高人民检察院",
]

_LAW_ALIAS_MAP: Optional[Dict[str, str]] = None


def _normalize_law_name(keyword: str) -> str:
    if not keyword:
        return ""

    cleaned = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]+", "", keyword)
    if not cleaned:
        return ""

    for prefix in COMMON_LAW_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    return cleaned


def _load_law_alias_map() -> Dict[str, str]:
    global _LAW_ALIAS_MAP
    if _LAW_ALIAS_MAP is not None:
        return _LAW_ALIAS_MAP

    alias_map: Dict[str, str] = {}
    alias_path = Path(__file__).resolve().parents[1] / "data" / "law_aliases.json"
    if alias_path.exists():
        try:
            data = json.loads(alias_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for canonical, aliases in data.items():
                    norm_key = _normalize_law_name(canonical)
                    if norm_key:
                        alias_map[norm_key] = canonical
                    if isinstance(aliases, list):
                        for alias in aliases:
                            norm_alias = _normalize_law_name(alias)
                            if norm_alias:
                                alias_map[norm_alias] = canonical
        except Exception:
            alias_map = {}

    _LAW_ALIAS_MAP = alias_map
    return alias_map


def _resolve_law_alias(keyword: str) -> str:
    normalized = _normalize_law_name(keyword)
    if not normalized:
        return ""
    return _load_law_alias_map().get(normalized, normalized)


def get_law_weight(title: str) -> int:
    """根据法律标题获取权重"""
    # 精确匹配
    if title in LAW_WEIGHT_CONFIG:
        return LAW_WEIGHT_CONFIG[title]
    # 模糊匹配（包含关键词）
    for key, weight in LAW_WEIGHT_CONFIG.items():
        if key in title:
            return weight
    return DEFAULT_WEIGHT


class LawService:
    """法规服务类"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.laws_collection = db.laws
        self.articles_collection = db.law_articles
        self.view_logs_collection = db.view_logs

    async def create_law(self, law_in: LawCreate) -> Dict[str, Any]:
        """创建法规（包含条文）"""
        # 1. 生成 ID
        law_id = hashlib.md5(law_in.title.encode()).hexdigest()[:16]
        
        # 2. 准备法规主档数据
        law_data = law_in.dict(exclude={"articles"})
        law_data["law_id"] = law_id
        # 为了避免全文过大，这里可以简单拼接前几条作为 full_text, 或者存空字符串
        # 更好的做法是把所有 content 拼起来
        full_text = "\n".join([a["content"] for a in law_in.articles])
        law_data["full_text"] = full_text
        
        # upsert 法规
        await self.laws_collection.replace_one(
            {"law_id": law_id}, law_data, upsert=True
        )
        
        # 3. 准备条文数据
        # 先删除旧条文
        await self.articles_collection.delete_many({"law_id": law_id})
        
        article_docs = []
        for art in law_in.articles:
            art_doc = {
                "law_id": law_id,
                "article_num": art["article_num"],
                "article_display": art["article_display"],
                "content": art["content"],
                "chapter": art.get("chapter", ""),
                "section": art.get("section", ""),
                "keywords": [] # TODO: 提取关键词
            }
            article_docs.append(art_doc)
            
        if article_docs:
            await self.articles_collection.insert_many(article_docs)
            
        return {"law_id": law_id, "message": f"成功导入 {len(article_docs)} 条条文"}

    async def get_laws_list(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        level: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取法规列表（分页 + 筛选）
        """
        # 构建查询条件
        query = {}
        if category:
            query["category"] = category
        if level:
            query["level"] = level
        if status:
            query["status"] = status
        if tags:
            query["tags"] = {"$in": tags}
        if title:
            query["title"] = {"$regex": title, "$options": "i"}

        # 计算总数
        total = await self.laws_collection.count_documents(query)

        # 计算分页
        skip = (page - 1) * page_size
        total_pages = math.ceil(total / page_size)

        # 查询数据（排除全文字段以提高性能）
        cursor = self.laws_collection.find(
            query, {"full_text": 0}
        ).sort("effect_date", -1).skip(skip).limit(page_size)

        laws = await cursor.to_list(length=page_size)

        # 转换 ObjectId 为字符串
        for law in laws:
            law["_id"] = str(law["_id"])

        return {
            "data": laws,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }

    async def get_law_detail(self, law_id: str) -> Optional[Dict[str, Any]]:
        """
        获取法规详情（包含全文）
        """
        law = await self.laws_collection.find_one({"law_id": law_id})
        if law:
            law["_id"] = str(law["_id"])
        return law

    async def update_law(self, law_id: str, update_data: Dict[str, Any]) -> bool:
        """
        更新法规信息
        """
        # 只允许更新特定字段
        allowed_fields = {"status", "category", "level", "issue_org", "issue_date", "effect_date", "expire_date", "summary"}
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            return False
            
        result = await self.laws_collection.update_one(
            {"law_id": law_id},
            {"$set": filtered_data}
        )
        return result.matched_count > 0

    async def delete_law(self, law_id: str) -> bool:
        """
        删除法规及其所有条文
        """
        # 先检查法规是否存在
        law = await self.laws_collection.find_one({"law_id": law_id})
        if not law:
            return False
            
        # 删除所有关联条文
        await self.articles_collection.delete_many({"law_id": law_id})
        # 删除法规主记录
        await self.laws_collection.delete_one({"law_id": law_id})
        return True

    async def get_law_articles(
        self, law_id: str, chapter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取法规的所有条文
        """
        query = {"law_id": law_id}
        if chapter:
            query["chapter"] = chapter

        cursor = self.articles_collection.find(query).sort("article_num", 1)
        articles = await cursor.to_list(length=None)

        for article in articles:
            article["_id"] = str(article["_id"])

        return articles

    async def get_article_by_number(
        self, law_id: str, article_num: int
    ) -> Optional[Dict[str, Any]]:
        """
        根据条号获取条文
        通过将阿拉伯数字转换为中文，匹配 article_display 字段
        """
        # 将阿拉伯数字转换为中文数字
        chinese_num = self._arabic_to_chinese(article_num)
        display_pattern = f"^第{chinese_num}条"
        
        article = await self.articles_collection.find_one({
            "law_id": law_id,
            "article_display": {"$regex": display_pattern}
        })
        if article:
            article["_id"] = str(article["_id"])
        return article
    
    def _arabic_to_chinese(self, num: int, full_form: bool = False) -> str:
        """
        阿拉伯数字转中文数字（支持1-999）
        full_form: 当为True时，10-19会转换为"一十"而不是"十"
        """
        if num <= 0:
            return "零"
        
        digits = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
        
        if num < 10:
            return digits[num]
        elif num < 20:
            # 十到十九
            # 当 full_form=True 或单独使用时，10="一十"，11="一十一"
            # 当 full_form=False（默认，用于条文首字），10="十"，11="十一"
            prefix = "一" if full_form else ""
            return prefix + "十" + (digits[num % 10] if num % 10 != 0 else "")
        elif num < 100:
            # 二十到九十九
            tens = num // 10
            ones = num % 10
            result = digits[tens] + "十"
            if ones > 0:
                result += digits[ones]
            return result
        elif num < 1000:
            hundreds = num // 100
            remainder = num % 100
            result = digits[hundreds] + "百"
            if remainder >= 10:
                # 百位后的10-19需要完整形式，如110="一百一十"
                result += self._arabic_to_chinese(remainder, full_form=True)
            elif remainder > 0:
                result += "零" + digits[remainder]
            return result
        else:
            return str(num)  # 超过999直接返回数字

    def parse_article_input(self, input_str: str) -> Optional[int]:
        """
        解析条号输入，支持多种格式：
        - "第八十三条" → 83
        - "83条" → 83
        - "83" → 83
        """
        # 中文数字映射
        chinese_num_map = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000
        }

        # 匹配模式1: 第XX条
        pattern1 = r'第([零一二三四五六七八九十百千]+)条'
        match = re.search(pattern1, input_str)
        if match:
            chinese_num = match.group(1)
            return self._chinese_to_arabic(chinese_num, chinese_num_map)

        # 匹配模式2: XX条
        pattern2 = r'(\d+)条'
        match = re.search(pattern2, input_str)
        if match:
            return int(match.group(1))

        # 匹配模式3: 纯数字
        pattern3 = r'^\d+$'
        if re.match(pattern3, input_str.strip()):
            return int(input_str.strip())

        return None

    def _extract_law_keyword(self, query: str) -> str:
        """
        Extract law name part from a query that includes an article number.
        """
        if not query:
            return ""

        cn_nums = "\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343"
        text = re.sub(rf"\u7b2c?[{cn_nums}]+\u6761", " ", query)
        text = re.sub(r"\u7b2c?\d+\u6761", " ", text)

        return text.strip()

    def _normalize_law_keyword(self, keyword: str) -> str:
        """
        Normalize law keyword for fuzzy title matching.
        """
        return _normalize_law_name(keyword)

    def _build_title_fuzzy_regex(self, keyword: str) -> Optional[str]:
        """
        Build a fuzzy regex that requires all tokens to appear in the title.
        """
        if not keyword or len(keyword) <= 1:
            return None

        if len(keyword) <= 4:
            tokens = list(keyword)
        else:
            tokens = [keyword[i:i + 2] for i in range(len(keyword) - 1)]

        tokens = [t for t in tokens if t.strip()]
        if not tokens:
            return None

        lookaheads = "".join(f"(?=.*{re.escape(t)})" for t in tokens)
        return f"{lookaheads}.*"

    async def _find_laws_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Find candidate laws by keyword using exact-substring, then fuzzy match.
        """
        if not keyword:
            return []

        exact = await self.laws_collection.find(
            {"title": {"$regex": re.escape(keyword), "$options": "i"}},
            {"full_text": 0},
        ).to_list(length=20)
        if exact:
            return exact

        fuzzy_regex = self._build_title_fuzzy_regex(keyword)
        if not fuzzy_regex:
            return []

        return await self.laws_collection.find(
            {"title": {"$regex": fuzzy_regex, "$options": "i"}},
            {"full_text": 0},
        ).to_list(length=20)

    async def _search_by_law_article(
        self, query: str, article_num: int, page: int, page_size: int
    ) -> Optional[Dict[str, Any]]:
        """
        Search by law name + article number pattern.
        """
        raw_keyword = self._extract_law_keyword(query)
        if not raw_keyword:
            return None

        keywords = []
        resolved = _resolve_law_alias(raw_keyword)
        if resolved:
            keywords.append(resolved)
        normalized = _normalize_law_name(raw_keyword)
        if normalized and normalized not in keywords:
            keywords.append(normalized)

        laws = []
        for keyword in keywords:
            laws = await self._find_laws_by_keyword(keyword)
            if laws:
                break
        if not laws:
            return None

        law_map = {law["law_id"]: law for law in laws}
        law_ids = list(law_map.keys())

        search_query = {"law_id": {"$in": law_ids}, "article_num": article_num}
        total = await self.articles_collection.count_documents(search_query)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        skip = (page - 1) * page_size

        cursor = self.articles_collection.find(search_query).skip(skip).limit(page_size)
        articles = await cursor.to_list(length=page_size)

        results = []
        for article in articles:
            article["_id"] = str(article["_id"])
            law_info = law_map.get(article["law_id"], {})
            results.append({
                "law_id": article["law_id"],
                "law_title": law_info.get("title", ""),
                "law_category": law_info.get("category", ""),
                "article_num": article.get("article_num"),
                "article_display": article.get("article_display", ""),
                "content": article.get("content", ""),
                "highlight": self._generate_highlight(
                    article.get("content", ""), normalized
                ),
            })

        return {
            "data": results,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }

    def _chinese_to_arabic(self, chinese_num: str, num_map: Dict[str, int]) -> int:
        """
        中文数字转阿拉伯数字
        支持：一、十、十一、二十、二十三、一百、一百零三、一千等
        """
        if not chinese_num:
            return 0

        result = 0
        current = 0

        for char in chinese_num:
            num = num_map.get(char, 0)
            if num >= 10:  # 单位（十、百、千）
                if current == 0:
                    current = 1
                result += current * num
                current = 0
            else:
                current = num

        return result + current

    async def search_in_law(
        self, law_id: str, query: str, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        在单个法规内搜索 - 支持条号和关键字
        
        搜索策略：
        1. 首先尝试解析为条号（如"第八十三条"、"83"）
        2. 如果不是条号，使用正则表达式搜索
        """
        # 先尝试解析为条号
        article_num = self.parse_article_input(query)

        if article_num:
            # 按条号精准查询
            article = await self.get_article_by_number(law_id, article_num)
            if article:
                return {
                    "data": [article],
                    "pagination": {
                        "total": 1,
                        "page": 1,
                        "page_size": page_size,
                        "total_pages": 1,
                    }
                }

        # 使用正则表达式搜索（确保准确性）
        search_query = {
            "law_id": law_id,
            "content": {"$regex": query, "$options": "i"}
        }
        total = await self.articles_collection.count_documents(search_query)
        
        # 分页参数
        skip = (page - 1) * page_size
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        # 按条号排序
        cursor = self.articles_collection.find(search_query).sort("article_num", 1).skip(skip).limit(page_size)
        results = await cursor.to_list(length=page_size)

        for result in results:
            result["_id"] = str(result["_id"])
            result["highlight"] = self._generate_highlight(result["content"], query)

        return {
            "data": results,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }

    async def search_global(
        self, query: str, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        全库搜索（跨法规）- 使用正则表达式确保准确性
        
        注意：MongoDB 文本索引对中文支持不完善，会漏掉大量结果。
        为确保搜索准确性（100%不漏），直接使用正则表达式搜索。
        
        排序策略：按法律权重降序 + 条号升序
        """
        import time
        start_time = time.time()

        article_num = self.parse_article_input(query)
        if article_num:
            article_result = await self._search_by_law_article(query, article_num, page, page_size)
            if article_result is not None:
                return article_result

        search_engine = get_search_engine()
        if search_engine.enabled:
            try:
                engine_result = await search_engine.search_articles(query, page, page_size)
                if engine_result is not None:
                    return engine_result
            except Exception:
                pass

        # 使用正则表达式搜索（确保准确性，任何子字符串都能被找到）
        search_query = {"content": {"$regex": query, "$options": "i"}}
        total = await self.articles_collection.count_documents(search_query)
        
        # 获取所有匹配结果（用于权重排序）
        # 注意：对于大量数据，这种方式可能比较慢，但能保证排序准确
        pipeline = [
            {"$match": search_query},
            {
                "$lookup": {
                    "from": "laws",
                    "localField": "law_id",
                    "foreignField": "law_id",
                    "as": "law_info",
                }
            },
            {"$unwind": "$law_info"},
            {
                "$project": {
                    "_id": 1,
                    "law_id": 1,
                    "law_title": "$law_info.title",
                    "law_category": "$law_info.category",
                    "article_num": 1,
                    "article_display": 1,
                    "content": 1,
                }
            }
        ]

        results = await self.articles_collection.aggregate(pipeline).to_list(length=None)
        
        # 按权重排序（权重降序，同权重按条号升序）
        results.sort(key=lambda x: (-get_law_weight(x.get("law_title", "")), x.get("article_num", 0)))
        
        # 分页
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        skip = (page - 1) * page_size
        paged_results = results[skip:skip + page_size]

        for result in paged_results:
            result["_id"] = str(result["_id"])
            result["highlight"] = self._generate_highlight(result["content"], query)

        elapsed_time = time.time() - start_time
        print(f"🔍 搜索完成: query=\"{query}\" | results={total} | time={elapsed_time:.3f}s")

        return {
            "data": paged_results,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }

    def _generate_highlight(self, content: str, query: str, context_length: int = 100) -> str:
        """
        生成高亮片段
        """
        # 简单实现：查找关键字第一次出现的位置，返回上下文
        index = content.find(query)
        if index == -1:
            # 如果没找到精确匹配，返回前 context_length 字符
            return content[:context_length] + ("..." if len(content) > context_length else "")

        start = max(0, index - context_length // 2)
        end = min(len(content), index + len(query) + context_length // 2)

        snippet = content[start:end]

        # 添加省略号
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    async def get_categories(self) -> List[str]:
        """获取所有法规分类（只返回数据库中实际存在的分类）"""
        categories = await self.laws_collection.distinct("category")
        # 过滤空值并排序
        return sorted([c for c in categories if c])

    async def get_levels(self) -> List[str]:
        """
        获取所有效力层级
        """
        levels = await self.laws_collection.distinct("level")
        return sorted(levels)

    async def record_view(self, law_id: str) -> bool:
        """记录一次法规浏览"""
        doc = {
            "law_id": law_id,
            "viewed_at": datetime.utcnow()
        }
        await self.view_logs_collection.insert_one(doc)
        return True

    async def get_today_views(self) -> int:
        """获取今日浏览总数"""
        # 获取今天 UTC 0点
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await self.view_logs_collection.count_documents({
            "viewed_at": {"$gte": today}
        })
        return count

    async def get_total_views(self) -> int:
        """Get total view count."""
        return await self.view_logs_collection.count_documents({})
