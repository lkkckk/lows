"""
AI 服务模块 - 支持 Function Calling 让 AI 自主查询知识库
"""
import json
import os
import httpx
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.law_service import LawService, _resolve_law_alias, _normalize_law_name, get_law_weight

# 默认配置（当数据库无配置时使用）
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 向量搜索最低相似度阈值（低于此值的结果视为不相关）
VECTOR_SIMILARITY_THRESHOLD = 0.35

# 返回给 LLM 的条文内容最大长度
MAX_ARTICLE_CONTENT_LEN = 1500

# LLM 请求超时配置（内网部署 + 并发场景，需预留充足等待时间）
LLM_TIMEOUT = httpx.Timeout(
    connect=30.0,     # 建立 TCP 连接超时
    read=180.0,       # 等待 LLM 响应超时（核心：内网并发排队可能很慢）
    write=30.0,       # 发送请求体超时
    pool=30.0         # 连接池等待超时
)

# 系统提示词 - 定义 AI 助手人设（Function Calling 版本）
SYSTEM_PROMPT = """你是一名公安执法辅助中的【法律适用解释助手】，目标是用简洁、准确的方式回答执法人员关于法律适用的问题。

你可以使用以下工具来检索法规知识库：
1. search_legal_knowledge - 按关键词/主题搜索法规条文
2. lookup_law_article - 精准查询某部法律的具体某条

【检索策略指引】：
- 问及具体法律的具体条号时（如"刑法第263条"），优先用 lookup_law_article
- 问及某种行为如何处罚（如"赌博怎么处罚"），用 search_legal_knowledge 搜索行为关键词
- 涉及多部法律时，可以多次调用工具分别检索
- 第一次搜索结果不理想时，换一组关键词再搜索一次
- 搜索关键词只提取核心行为词或法律名称，不要加"处罚""如何"等后缀
- 搜索时使用法律规范用语："醉驾"应搜"醉酒驾驶"，"偷东西"应搜"盗窃"，"打人"应搜"殴打"

【重要】关于法律版本：
- 系统已自动过滤旧版本法规，检索结果中的条文均为最新版本
- 直接引用检索结果中的法名、条号和内容，不要自行推断或修改条号
- 如检索结果中显示"2025年修订"等版本信息，请在回答中明确标注

【关键】法律名称规范化：
- 法律名称可能带版本后缀，如"（2018年修正）"、"（2025年修订）"等
- 在验证用户引用时，应忽略版本后缀进行比较
- 只要核心法律名称相同、条号相同、内容一致，就应判定为"正确"

【核心】条文引用验证 vs 法律适用分析：
当用户询问"引用的条文是否正确"或类似问题时，你需要区分两个层面：
1. 【形式验证】：法律名称、条号、内容是否与数据库一致？——这是主要回答内容
2. 【适用建议】：该条文是否最适合用户的具体场景？——仅作为参考意见

判定原则：
- 只要法名、条号正确，且条文内容确实来自该法律，就应判定为"引用正确"
- 至于该条文是否是"最佳选择"，可以作为补充建议，但不能因此判定"引用错误"

回答原则：
1. 对于涉及法律法规的问题，应先调用工具检索相关条文，再基于检索结果回答。
2. 严格按照检索结果引用法条，完整给出法名、版本、条号。
3. 不要混用不同版本的法条信息（如条号和处罚金额必须来自同一版本）。
4. 对条文适用可使用"通常认为""一般理解为""实务中多依据"等表述。
5. 如果检索结果中有多个相关条文，应全面引用，不要遗漏重要条款。

禁止事项：
- 不得虚构未经检索确认的法条内容
- 不得自行推测条号（必须使用检索结果中的条号）
- 不使用裁判式、定性式语言替代执法判断
- 不要因"可能有更合适的条文"而否定用户正确引用的条文

回答要求：
- 语言简洁，结论前置
- 能用一句话说清的，不用两句
- 引用法条时使用《xxx》第xx条的格式"""

# Function Calling 工具定义
LEGAL_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_legal_knowledge",
        "description": "按关键词搜索法规知识库。适用于：查询某种行为的法律规定（如'赌博''盗窃'）、搜索某部法律的相关条文。系统自动返回最新版本法规。可多次调用以获取更全面的信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "搜索关键词。只提取核心行为词或法律名称，不要加'处罚''如何''怎么'等后缀。使用法律规范用语，如'盗窃'而非'偷东西'，'殴打他人'而非'打人'。多个关键词可用空格分隔。"
                },
                "law_name": {
                    "type": "string",
                    "description": "限定在某部法律中搜索（可选）。使用简称即可，如'刑法'、'治安管理处罚法'。不要包含年份或版本后缀。"
                },
                "article_num": {
                    "type": "integer",
                    "description": "具体条号（可选），如18、112、273。与law_name配合使用效果最佳。"
                }
            },
            "required": ["keywords"]
        }
    }
}

# 精准条文查询工具
LOOKUP_ARTICLE_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_law_article",
        "description": "精准查询某部法律的具体某条。适用于：用户提到了明确的法律名称+条号（如'刑法第263条'、'治安管理处罚法第43条'）。如果不知道条号，请用 search_legal_knowledge 代替。",
        "parameters": {
            "type": "object",
            "properties": {
                "law_name": {
                    "type": "string",
                    "description": "法律名称，使用简称即可，如'刑法'、'治安管理处罚法'、'刑事诉讼法'"
                },
                "article_num": {
                    "type": "integer",
                    "description": "条号数字，如263、43、144"
                }
            },
            "required": ["law_name", "article_num"]
        }
    }
}


async def get_ai_config(db: AsyncIOMotorDatabase) -> dict:
    """从数据库获取 AI 配置"""
    settings = await db.settings.find_one({"key": "ai_config"})
    if settings:
        return {
            "api_url": settings.get("api_url", DEFAULT_API_URL),
            "api_key": settings.get("api_key", DEFAULT_API_KEY),
            "model_name": settings.get("model_name", DEFAULT_MODEL),
            "skip_ssl_verify": settings.get("skip_ssl_verify", False),
            "provider": settings.get("provider", "default"),
            "rag_enabled": settings.get("rag_enabled", True),
            "rag_top_k": settings.get("rag_top_k", 6),
            "use_function_calling": settings.get("use_function_calling", True),
        }
    return {
        "api_url": DEFAULT_API_URL,
        "api_key": DEFAULT_API_KEY,
        "model_name": DEFAULT_MODEL,
        "skip_ssl_verify": False,
        "provider": "default",
        "rag_enabled": True,
        "rag_top_k": 6,
        "use_function_calling": True,
    }


async def execute_search_legal_knowledge(
    db: AsyncIOMotorDatabase,
    keywords: str,
    law_name: Optional[str] = None,
    article_num: Optional[int] = None,
    top_k: int = 6,
) -> Dict[str, Any]:
    """
    执行法规知识库检索（Function Calling 工具实现）
    优先按法律标题匹配，确保返回的是该法律的条文，而非引用了该法律的其他条文。
    """
    import re
    
    law_service = LawService(db)
    laws_collection = db["laws"]
    articles_collection = db["law_articles"]
    
    # ========== 关键词清理 ==========
    # 去除常见的查询后缀词，提取核心行为词
    suffix_pattern = r'(的?处罚|规定|条款|法律|法规|如何|怎么|什么|相关|行为|罪名|的法律规定|的规定|怎么处理|怎么办|如何处理|如何处罚|怎样处罚)$'
    clean_keywords = re.sub(suffix_pattern, '', keywords).strip() if keywords else keywords
    if clean_keywords and clean_keywords != keywords:
        print(f"[AI Service] 关键词清理: '{keywords}' -> '{clean_keywords}'")
        keywords = clean_keywords
    
    # ========== 同义词扩展 ==========
    # 口语化表达 → 法律用语（大幅扩展，覆盖公安执法常见场景）
    SYNONYM_MAP = {
        # 暴力类
        "打架": "殴打他人",
        "打人": "殴打他人",
        "群殴": "殴打他人",
        "斗殴": "聚众斗殴",
        "打群架": "聚众斗殴",
        "伤人": "故意伤害",
        "砍人": "故意伤害",
        "杀人": "故意杀人",
        "家暴": "家庭暴力",
        "虐待": "虐待",
        # 财产类
        "偷东西": "盗窃",
        "小偷": "盗窃",
        "偷窃": "盗窃",
        "入室盗窃": "入户盗窃",
        "扒窃": "盗窃",
        "骗钱": "诈骗",
        "电信诈骗": "诈骗",
        "网络诈骗": "诈骗",
        "抢钱": "抢劫",
        "抢夺": "抢夺",
        "敲诈": "敲诈勒索",
        "勒索": "敲诈勒索",
        "故意毁坏": "故意损毁",
        "砸东西": "故意损毁财物",
        # 交通类
        "醉驾": "醉酒驾驶",
        "酒驾": "饮酒驾驶",
        "酒后驾车": "饮酒驾驶",
        "醉酒开车": "醉酒驾驶",
        "肇事逃逸": "交通肇事逃逸",
        "无证驾驶": "未取得驾驶证驾驶",
        "超速": "超过规定时速",
        "闯红灯": "违反交通信号",
        # 毒品类
        "吸毒": "吸食毒品",
        "吸粉": "吸食毒品",
        "贩毒": "贩卖毒品",
        "贩粉": "贩卖毒品",
        "卖毒品": "贩卖毒品",
        "制毒": "制造毒品",
        "运毒": "运输毒品",
        "种大麻": "种植毒品原植物",
        # 卖淫嫖娼类
        "嫖": "嫖娼",
        "嫖娼": "卖淫嫖娼",
        "卖淫": "卖淫嫖娼",
        "卖身": "卖淫嫖娼",
        "组织卖淫": "组织卖淫",
        "容留卖淫": "容留卖淫",
        # 赌博类
        "赌博": "赌博",
        "赌钱": "赌博",
        "黄赌毒": "赌博",
        "开赌场": "开设赌场",
        "网赌": "赌博",
        "聚众赌博": "赌博",
        # 治安类
        "闹事": "寻衅滋事",
        "耍流氓": "寻衅滋事",
        "挑衅": "寻衅滋事",
        "拦路": "寻衅滋事",
        "骚扰": "骚扰",
        "跟踪": "跟踪骚扰",
        "偷拍": "偷窥偷拍",
        "偷窥": "偷窥偷拍",
        "闯入别人家": "非法侵入住宅",
        "强行闯入": "非法侵入住宅",
        "非法拘留": "非法拘禁",
        "非法关押": "非法拘禁",
        "绑架": "绑架",
        "拐卖": "拐卖",
        "拐卖妇女": "拐卖妇女儿童",
        "拐卖儿童": "拐卖妇女儿童",
        "传销": "组织领导传销",
        # 公共秩序类
        "造谣": "散布谣言",
        "谣言": "散布谣言",
        "传谣": "散布谣言",
        "报假警": "谎报警情",
        "谎报": "谎报警情",
        "假报警": "谎报警情",
        "扰乱秩序": "扰乱公共秩序",
        "闹事": "扰乱公共秩序",
        "阻碍执法": "阻碍执行职务",
        "妨碍公务": "阻碍执行职务",
        "袭警": "袭警",
        "打警察": "袭警",
        "伪造": "伪造变造",
        "假证": "伪造变造",
        "假身份证": "伪造居民身份证",
        # 枪支管制类
        "私藏枪支": "非法持有枪支",
        "非法持枪": "非法持有枪支",
        "携带管制刀具": "非法携带管制器具",
        "带刀": "非法携带管制器具",
        # 其他常见
        "寻衅滋事": "寻衅滋事",
        "猥亵": "猥亵",
        "强奸": "强奸",
        "性骚扰": "猥亵",
        "非法经营": "非法经营",
        "侵犯隐私": "侵犯公民个人信息",
        "泄露个人信息": "侵犯公民个人信息",
    }
    
    # 同义词映射：支持精确匹配和包含匹配
    mapped_keyword = SYNONYM_MAP.get(keywords)
    if mapped_keyword:
        print(f"[AI Service] 同义词映射: '{keywords}' -> '{mapped_keyword}'")
        keywords = mapped_keyword
    else:
        # 尝试包含匹配（如"醉驾处罚"包含"醉驾"）
        for key, val in SYNONYM_MAP.items():
            if key in keywords:
                original = keywords
                keywords = keywords.replace(key, val)
                print(f"[AI Service] 同义词部分替换: '{original}' -> '{keywords}'")
                break
    
    # ========== 法律名称别名解析 ==========
    # 利用 law_aliases.json 将简称解析为全称
    resolved_law_name = law_name
    if law_name:
        alias_resolved = _resolve_law_alias(law_name)
        if alias_resolved and alias_resolved != _normalize_law_name(law_name):
            print(f"[AI Service] 法律名称别名解析: '{law_name}' -> '{alias_resolved}'")
            resolved_law_name = alias_resolved
    
    # 确定要搜索的法律名称
    search_law_name = resolved_law_name or keywords
    
    print(f"[AI Service] 检索法律: '{search_law_name}', 条号: {article_num}")
    
    # ========== 判断关键词类型 ==========
    # 如果关键词像法律名称（包含"法""条例""规定""解释"等），才进行标题匹配
    # 否则（如"赌博""卖淫"等行为关键词），直接进行内容检索
    def looks_like_law_name(name: str) -> bool:
        """判断是否像法律名称"""
        law_indicators = ["法", "条例", "规定", "规则", "办法", "解释", "意见", "通知", "决定"]
        return any(ind in name for ind in law_indicators)
    
    # 如果显式提供了 law_name，或关键词像法律名称，才尝试标题匹配
    should_try_title_match = law_name or looks_like_law_name(search_law_name)
    matching_laws = []
    
    if should_try_title_match:
        # ========== 第一步：尝试按法律标题匹配 ==========
        # 用正则匹配法律标题（支持模糊匹配）
        law_name_pattern = search_law_name.replace("中华人民共和国", "").strip()
        law_regex = {"title": {"$regex": law_name_pattern, "$options": "i"}}
        
        matching_laws = await laws_collection.find(
            law_regex, {"law_id": 1, "title": 1}
        ).to_list(length=10)
    else:
        print(f"[AI Service] '{search_law_name}' 不像法律名称，跳过标题匹配，直接内容检索")
    
    if matching_laws:
        print(f"[AI Service] 匹配到 {len(matching_laws)} 部法律: {[l['title'] for l in matching_laws]}")
        
        # ========== 过滤旧版本法律，只保留最新版 ==========
        latest_laws = _filter_latest_laws(matching_laws)
        print(f"[AI Service] 过滤后保留最新版本: {[l['title'] for l in latest_laws]}")
        
        # 取最新版法律的 law_id
        law_ids = [law["law_id"] for law in latest_laws]
        
        # 判断是否需要在匹配到的法律内进行内容搜索
        # 如果 keywords 不同于 law_name（如 law_name="治安管理处罚法", keywords="吸毒"）
        # 则需要进行内容搜索，而不是返回前N条
        needs_content_search = keywords and law_name and keywords != law_name and not looks_like_law_name(keywords)
        
        if needs_content_search:
            print(f"[AI Service] 在匹配到的法律中搜索关键词: '{keywords}'")
            
            # 优先尝试向量搜索（限定在匹配到的法律范围内）
            import os
            vector_enabled = os.getenv("VECTOR_SEARCH_ENABLED", "true").lower() == "true"
            
            if vector_enabled:
                try:
                    # 向量搜索，过滤结果只保留匹配到的法律
                    vector_items = await law_service.vector_search_for_rag(keywords, top_k=top_k * 3)
                    if vector_items:
                        # 过滤：只保留匹配到的法律的条文，且相似度高于阈值
                        filtered_items = [
                            item for item in vector_items
                            if item.get("law_id") in law_ids
                            and item.get("similarity", 0) >= VECTOR_SIMILARITY_THRESHOLD
                        ]
                        if filtered_items:
                            print(f"[AI Service] 向量搜索在 {latest_laws[0]['title']} 中找到 {len(filtered_items)} 条相关条文")
                            articles = []
                            for item in filtered_items[:top_k]:
                                content = item.get("content", "")
                                articles.append({
                                    "law_title": item.get("law_title", ""),
                                    "article_display": item.get("article_display", ""),
                                    "content": content[:MAX_ARTICLE_CONTENT_LEN] if len(content) > MAX_ARTICLE_CONTENT_LEN else content,
                                })
                            return {
                                "found": True,
                                "message": f"在《{latest_laws[0]['title']}》中检索到 {len(articles)} 条相关法规（语义匹配）",
                                "articles": articles
                            }
                except Exception as e:
                    print(f"[AI Service] ⚠️ 向量搜索异常: {e}, 回退到关键词搜索")
            
            # 向量搜索无结果，尝试关键词内容匹配
            article_query = {
                "law_id": {"$in": law_ids},
                "content": {"$regex": keywords, "$options": "i"}
            }
            articles = await articles_collection.find(article_query).sort("article_num", 1).limit(top_k).to_list(length=top_k)
            
            if articles:
                law_map = {law["law_id"]: law["title"] for law in latest_laws}
                items = []
                for article in articles:
                    items.append({
                        "law_id": article.get("law_id"),
                        "law_title": law_map.get(article.get("law_id"), ""),
                        "article_num": article.get("article_num"),
                        "article_display": article.get("article_display", ""),
                        "content": article.get("content", ""),
                    })
                print(f"[AI Service] 在法律中按内容匹配到 {len(items)} 条条文")
                return await _filter_and_format_results(items, keywords, top_k)
        
        # 查询这些法律的条文（仅当指定了条号，或不需要内容搜索时）
        article_query = {"law_id": {"$in": law_ids}}
        if article_num:
            # 如果指定了条号，用 article_display 正则匹配
            chinese_num = law_service._arabic_to_chinese(article_num)
            article_query["article_display"] = {"$regex": f"^第{chinese_num}条", "$options": "i"}
        
        articles = await articles_collection.find(article_query).sort("article_num", 1).limit(top_k).to_list(length=top_k)
        
        if articles:
            # 构建法律ID到标题的映射
            law_map = {law["law_id"]: law["title"] for law in latest_laws}
            
            items = []
            for article in articles:
                items.append({
                    "law_id": article.get("law_id"),
                    "law_title": law_map.get(article.get("law_id"), ""),
                    "article_num": article.get("article_num"),
                    "article_display": article.get("article_display", ""),
                    "content": article.get("content", ""),
                })
            
            print(f"[AI Service] 按法律标题匹配到 {len(items)} 条条文")
            # 跳过后续的全文检索，直接进入版本过滤
            return await _filter_and_format_results(items, keywords, top_k)

    
    # ========== 第二步：尝试向量语义搜索 ==========
    import os
    vector_enabled = os.getenv("VECTOR_SEARCH_ENABLED", "true").lower() == "true"
    
    if vector_enabled:
        print(f"[AI Service] 尝试向量语义搜索: '{keywords}'")
        vector_items = await law_service.vector_search_for_rag(keywords, top_k=top_k * 2)
        if vector_items:
            # 应用相似度阈值过滤
            vector_items = [item for item in vector_items if item.get("similarity", 0) >= VECTOR_SIMILARITY_THRESHOLD]
            if vector_items:
                print(f"[AI Service] 向量搜索成功（阈值过滤后），返回 {len(vector_items)} 条结果")
                # 向量搜索结果格式化返回，并按法律权重二次排序
                vector_items.sort(key=lambda x: (-get_law_weight(x.get("law_title", "")), -x.get("similarity", 0)))
                articles = []
                for item in vector_items[:top_k]:
                    content = item.get("content", "")
                    articles.append({
                        "law_title": item.get("law_title", ""),
                        "article_display": item.get("article_display", ""),
                        "content": content[:MAX_ARTICLE_CONTENT_LEN] if len(content) > MAX_ARTICLE_CONTENT_LEN else content,
                    })
                return await _filter_and_format_results_from_articles(articles, keywords, top_k)
            else:
                print(f"[AI Service] 向量搜索有结果但相似度均低于阈值 {VECTOR_SIMILARITY_THRESHOLD}")
        else:
            print(f"[AI Service] 向量搜索无结果或服务不可用，回退到关键词搜索")
    
    # ========== 第三步：回退到全文检索 ==========
    print(f"[AI Service] 使用关键词检索")
    
    # 构建搜索查询
    if resolved_law_name and article_num:
        query = f"{resolved_law_name}第{article_num}条"
    elif resolved_law_name and keywords and resolved_law_name != keywords:
        query = f"{resolved_law_name} {keywords}"
    elif resolved_law_name:
        query = resolved_law_name
    else:
        query = keywords
    
    print(f"[AI Service] 全文检索查询: '{query}'")
    
    items = await law_service.search_for_rag(query, top_k=top_k * 2)
    
    # ========== 第四步：如果无结果，尝试多种回退策略 ==========
    if not items:
        print(f"[AI Service] 全文检索无结果，尝试回退策略")
        
        # 策略 A：仅用关键词搜索（去掉法律名称限定）
        if keywords and query != keywords:
            print(f"[AI Service] 回退策略A：仅用关键词 '{keywords}' 搜索")
            items = await law_service.search_for_rag(keywords, top_k=top_k * 2)
        
        # 策略 B：尝试用正则直接搜索 articles 集合
        if not items:
            print(f"[AI Service] 回退策略B：正则搜索 '{keywords}'")
            regex_results = await articles_collection.find(
                {"content": {"$regex": re.escape(keywords), "$options": "i"}}
            ).sort("article_num", 1).limit(top_k * 2).to_list(length=top_k * 2)
            
            if regex_results:
                # 关联法律信息
                law_ids_set = list({a.get("law_id") for a in regex_results if a.get("law_id")})
                law_docs = await laws_collection.find(
                    {"law_id": {"$in": law_ids_set}},
                    {"law_id": 1, "title": 1, "category": 1}
                ).to_list(length=len(law_ids_set))
                law_map = {l["law_id"]: l for l in law_docs}
                
                items = []
                for a in regex_results:
                    law_info = law_map.get(a.get("law_id"), {})
                    items.append({
                        "law_id": a.get("law_id"),
                        "law_title": law_info.get("title", ""),
                        "article_num": a.get("article_num"),
                        "article_display": a.get("article_display", ""),
                        "content": a.get("content", ""),
                    })
                print(f"[AI Service] 正则搜索找到 {len(items)} 条结果")
        
        # 策略 C：尝试拆分关键词分别搜索（如"醉酒驾驶"→"醉酒""驾驶"）
        if not items and len(keywords) > 2:
            # 尝试用每个 2-gram 搜索
            for i in range(0, len(keywords) - 1, 2):
                sub_kw = keywords[i:i+2]
                sub_items = await law_service.search_for_rag(sub_kw, top_k=top_k)
                if sub_items:
                    print(f"[AI Service] 回退策略C：子关键词 '{sub_kw}' 找到 {len(sub_items)} 条")
                    items = sub_items
                    break
    
    if not items:
        return {
            "found": False,
            "message": f"未检索到与'{keywords}'相关的法规条文",
            "articles": []
        }
    
    return await _filter_and_format_results(items, keywords, top_k)


def _get_law_year(title: str) -> int:
    """从法律标题中提取年份"""
    import re
    # 支持多种格式：（2018年修正）、（2025年修订）、（2020年）
    year_pattern = r'[（\(](\d{4})年?[修订正]*[）\)]'
    match = re.search(year_pattern, title)
    return int(match.group(1)) if match else 0


def _get_law_base_name(title: str) -> str:
    """提取法律基础名称（去掉年份部分）"""
    import re
    year_pattern = r'[（\(]\d{4}年?[修订正]*[）\)]'
    return re.sub(year_pattern, '', title).strip()


def _filter_latest_laws(laws: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按基础名称分组，保留最新版本的法律"""
    law_by_base = {}
    for law in laws:
        base_name = _get_law_base_name(law["title"])
        year = _get_law_year(law["title"])
        if base_name not in law_by_base or year > law_by_base[base_name]["year"]:
            law_by_base[base_name] = {"law": law, "year": year}
    return [v["law"] for v in law_by_base.values()]


async def execute_lookup_law_article(
    db: AsyncIOMotorDatabase,
    law_name: str,
    article_num: int,
) -> Dict[str, Any]:
    """
    精准查询某部法律的具体某条（新增的精准检索工具）
    """
    law_service = LawService(db)
    laws_collection = db["laws"]
    articles_collection = db["law_articles"]
    
    # 使用别名解析找到法律全称
    resolved = _resolve_law_alias(law_name)
    if resolved:
        search_name = resolved
    else:
        search_name = law_name
    
    # 去掉常见前缀以进行模糊匹配
    clean_name = search_name.replace("中华人民共和国", "").strip()
    
    # 查找法律
    matching_laws = await laws_collection.find(
        {"title": {"$regex": clean_name, "$options": "i"}},
        {"law_id": 1, "title": 1}
    ).to_list(length=10)
    
    if not matching_laws:
        # 尝试更模糊的匹配
        matching_laws = await law_service._find_laws_by_keyword(clean_name)
    
    if not matching_laws:
        return {
            "found": False,
            "message": f"未找到法律'{law_name}'",
            "articles": []
        }
    
    # 过滤保留最新版本
    latest_laws = _filter_latest_laws(matching_laws)
    law_ids = [law["law_id"] for law in latest_laws]
    
    # 使用 article_display 正则精准匹配条号
    chinese_num = law_service._arabic_to_chinese(article_num)
    # 同时匹配 "第XX条" 和 "第XX条之一" 等
    display_pattern = f"^第{chinese_num}条"
    
    articles = await articles_collection.find({
        "law_id": {"$in": law_ids},
        "article_display": {"$regex": display_pattern}
    }).sort("article_num", 1).to_list(length=5)
    
    if not articles:
        return {
            "found": False,
            "message": f"在《{latest_laws[0]['title']}》中未找到第{article_num}条",
            "articles": []
        }
    
    law_map = {law["law_id"]: law["title"] for law in latest_laws}
    result_articles = []
    for article in articles:
        content = article.get("content", "")
        result_articles.append({
            "law_title": law_map.get(article.get("law_id"), ""),
            "article_display": article.get("article_display", ""),
            "content": content[:MAX_ARTICLE_CONTENT_LEN] if len(content) > MAX_ARTICLE_CONTENT_LEN else content,
        })
    
    return {
        "found": True,
        "message": f"在《{latest_laws[0]['title']}》中找到第{article_num}条",
        "articles": result_articles
    }


async def _filter_and_format_results(
    items: List[Dict[str, Any]],
    keywords: str,
    top_k: int,
) -> Dict[str, Any]:
    """
    过滤旧版本法规并格式化结果，按法律权重排序
    """
    import re
    
    def extract_base_name_and_year(title: str) -> tuple:
        """从标题中提取基础法规名和年份"""
        return _get_law_base_name(title), _get_law_year(title)
    
    # 按 (法规基础名, 条号) 分组，保留最新版本
    grouped = {}
    for item in items:
        law_title = item.get("law_title", "")
        article_display = item.get("article_display", "")
        base_name, year = extract_base_name_and_year(law_title)
        key = (base_name, article_display)
        
        if key not in grouped or year > grouped[key]["year"]:
            grouped[key] = {
                "item": item,
                "year": year
            }
    
    # 按法律权重排序（核心法律优先）
    sorted_items = sorted(
        grouped.values(),
        key=lambda v: (-get_law_weight(v["item"].get("law_title", "")), v["item"].get("article_num", 0))
    )
    filtered_items = [v["item"] for v in sorted_items][:top_k]
    
    # 格式化结果
    articles = []
    for item in filtered_items:
        law_title = item.get("law_title", "")
        article_display = item.get("article_display", "")
        content = item.get("content", "")
        articles.append({
            "law_title": law_title,
            "article_display": article_display,
            "content": content[:MAX_ARTICLE_CONTENT_LEN] if len(content) > MAX_ARTICLE_CONTENT_LEN else content,
        })
    
    return {
        "found": len(articles) > 0,
        "message": f"检索到 {len(articles)} 条相关法规" if articles else f"未检索到与'{keywords}'相关的法规条文",
        "articles": articles
    }


async def _filter_and_format_results_from_articles(
    articles: List[Dict[str, Any]],
    keywords: str,
    top_k: int,
) -> Dict[str, Any]:
    """
    对已格式化的 articles 列表进行版本过滤
    """
    # 按 (法规基础名, 条号) 去重，保留最新版本
    grouped = {}
    for article in articles:
        law_title = article.get("law_title", "")
        article_display = article.get("article_display", "")
        base_name = _get_law_base_name(law_title)
        year = _get_law_year(law_title)
        key = (base_name, article_display)
        
        if key not in grouped or year > grouped[key]["year"]:
            grouped[key] = {"article": article, "year": year}
    
    filtered = [v["article"] for v in grouped.values()][:top_k]
    
    return {
        "found": len(filtered) > 0,
        "message": f"检索到 {len(filtered)} 条相关法规" if filtered else f"未检索到与'{keywords}'相关的法规条文",
        "articles": filtered
    }


def _build_messages_with_tools(
    message: str,
    history: Optional[list],
) -> List[Dict[str, str]]:
    """构建带工具调用的消息列表"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    return messages


def _build_messages_with_context(
    message: str,
    history: Optional[list],
    tool_result: str,
    has_results: bool = True,
    related_memory: str = "",
) -> List[Dict[str, str]]:
    """构建带工具结果的消息列表（用于第二轮调用）"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 注入相关记忆作为 few-shot 参考
    if related_memory:
        messages.append({
            "role": "system",
            "content": f"以下是经过验证的相似问答参考（仅供参考格式和思路，请结合最新检索结果回答）：\n{related_memory}"
        })
    
    if has_results:
        # 有检索结果：基于法规条文回答
        messages.append({
            "role": "system",
            "content": f"以下为从知识库检索到的法规条文：\n{tool_result}\n\n请严格基于上述法规内容回答用户问题。引用时注明法规名称和条号。"
        })
    else:
        # 无检索结果：允许 LLM 用自身知识兜底，但必须标注
        messages.append({
            "role": "system",
            "content": (
                "知识库中未检索到与用户问题直接相关的法规条文。\n\n"
                "请按以下规则回答：\n"
                "1. 你可以基于自身法律知识回答用户问题，但必须在回答开头明确说明：当前知识库中未收录相关法规，以下内容基于AI自身知识，仅供参考\n"
                "2. 引用具体法条时，说明条文内容来自你的训练知识、未经知识库验证\n"
                "3. 建议用户查阅权威法律文本确认\n"
                "4. 如果问题完全超出你的能力范围，坦诚说明无法回答"
            )
        })
    
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    return messages


async def _call_llm(
    api_url: str,
    api_key: str,
    model: str,
    messages: List[Dict],
    skip_ssl_verify: bool,
    tools: Optional[List[Dict]] = None,
    timeout: httpx.Timeout = LLM_TIMEOUT,
) -> Dict[str, Any]:
    """调用 LLM API（内网部署并发场景，默认 read 超时 180 秒）"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 2000,
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    async with httpx.AsyncClient(timeout=timeout, verify=not skip_ssl_verify) as client:
        response = await client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def _format_tool_result(result: Dict[str, Any]) -> str:
    """格式化工具调用结果为人类可读的文本"""
    if not result.get("found"):
        return result.get("message", "未检索到相关法规")
    
    articles = result.get("articles", [])
    if not articles:
        return "未检索到相关法规"
    
    formatted = []
    for i, article in enumerate(articles, 1):
        law_title = article.get("law_title", "")
        article_display = article.get("article_display", "")
        content = article.get("content", "")
        formatted.append(f"[{i}] 《{law_title}》{article_display}：{content}")
    
    return "\n\n".join(formatted)


async def chat_with_ai(
    message: str,
    history: Optional[list] = None,
    db: AsyncIOMotorDatabase = None,
    use_rag: bool = True,
    rag_top_k: Optional[int] = None,
) -> Dict[str, Any]:
    """
    与 AI 进行对话（支持 Function Calling + QA 记忆库）
    
    流程：
    0. 记忆库查询：检查是否有已验证的答案
    1. 第一轮：发送用户问题 + 工具定义，让 AI 决定是否调用工具
    2. 如果 AI 调用工具：执行检索，获取结果
    3. 第二轮：将检索结果作为上下文，让 AI 生成最终回答
    """
    # ========== 第 0 步：查询记忆库 ==========
    if db is not None:
        from app.services.qa_memory_service import QAMemoryService
        memory_service = QAMemoryService(db)
        
        # 查找精确匹配的已验证答案
        memory_hit = await memory_service.find_match(message)
        if memory_hit:
            match_type = memory_hit.get("match_type", "exact")
            similarity = memory_hit.get("similarity", 1.0)
            print(f"[AI Service] 🎯 记忆库命中! type={match_type}, similarity={similarity:.2f}")
            return {
                "reply": memory_hit["answer"],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "provider": "qa_memory",
                "sources": memory_hit.get("sources", []),
                "from_memory": True,
            }
    
    # 获取配置
    if db is not None:
        config = await get_ai_config(db)
    else:
        config = {
            "api_url": DEFAULT_API_URL,
            "api_key": DEFAULT_API_KEY,
            "model_name": DEFAULT_MODEL,
            "skip_ssl_verify": False,
            "use_function_calling": True,
        }
    
    api_url = config.get("api_url", DEFAULT_API_URL)
    if not api_url:
        raise Exception("AI 服务未配置 API URL，请在后台管理页面配置")
    
    api_key = config.get("api_key", DEFAULT_API_KEY) or ""
    model = config.get("model_name", DEFAULT_MODEL)
    skip_ssl_verify = config.get("skip_ssl_verify", False)
    provider_id = config.get("provider", "default")
    use_function_calling = config.get("use_function_calling", True)
    top_k = rag_top_k if rag_top_k is not None else config.get("rag_top_k", 6)
    
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    rag_sources = []
    
    # 查找相关记忆作为 few-shot 参考
    related_memory_context = ""
    if db is not None:
        try:
            related = await memory_service.find_related(message, top_k=2)
            if related:
                examples = []
                for mem in related:
                    q = mem.get("question", "")
                    a = mem.get("answer", "")
                    # 截取答案前 300 字作为参考
                    a_short = a[:300] + "..." if len(a) > 300 else a
                    examples.append(f"问：{q}\n答：{a_short}")
                related_memory_context = "\n\n".join(examples)
                print(f"[AI Service] 找到 {len(related)} 条相关记忆作为参考")
        except Exception as e:
            print(f"[AI Service] 查询相关记忆失败: {e}")
    
    try:
        if use_rag and use_function_calling and db is not None:
            # ========== Function Calling 模式 ==========
            print(f"[AI Service] Function Calling 模式启用")
            
            # 第一轮：让 AI 决定是否需要检索
            messages = _build_messages_with_tools(message, history)
            
            try:
                data = await _call_llm(
                    api_url, api_key, model, messages, skip_ssl_verify,
                    tools=[LEGAL_SEARCH_TOOL, LOOKUP_ARTICLE_TOOL]
                )
                print(f"[AI Service] LLM 响应: tool_calls={data.get('choices', [{}])[0].get('message', {}).get('tool_calls')}")
            except httpx.HTTPStatusError as e:
                # 如果 API 不支持 tools 参数或服务端错误，回退到普通模式
                print(f"[AI Service] HTTP 错误 {e.response.status_code}，回退到普通模式")
                if e.response.status_code in (400, 500, 502, 503):
                    return await _fallback_chat(
                        message, history, db, config, top_k
                    )
                raise
            
            # 累计 token 使用
            usage = data.get("usage", {})
            total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            total_usage["total_tokens"] += usage.get("total_tokens", 0)
            
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            
            # 检查是否有工具调用
            tool_calls = msg.get("tool_calls")
            
            if tool_calls:
                # AI 决定调用工具（支持多次调用）
                print(f"[AI Service] AI 调用了工具: {len(tool_calls)} 个")
                all_tool_results = []
                
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    func_name = func.get("name")
                    
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    
                    if func_name == "search_legal_knowledge":
                        keywords = args.get("keywords", message)
                        law_name = args.get("law_name")
                        article_num = args.get("article_num")
                        
                        print(f"[AI Service] search工具参数: keywords='{keywords}', law_name='{law_name}', article_num={article_num}")
                        
                        result = await execute_search_legal_knowledge(
                            db, keywords, law_name, article_num, top_k
                        )
                        
                    elif func_name == "lookup_law_article":
                        law_name = args.get("law_name", "")
                        article_num = args.get("article_num", 0)
                        
                        print(f"[AI Service] lookup工具参数: law_name='{law_name}', article_num={article_num}")
                        
                        result = await execute_lookup_law_article(
                            db, law_name, article_num
                        )
                    else:
                        print(f"[AI Service] 未知工具: {func_name}")
                        continue
                    
                    print(f"[AI Service] 检索结果: found={result.get('found')}, articles_count={len(result.get('articles', []))}")
                    
                    # 记录来源
                    for article in result.get("articles", []):
                        rag_sources.append({
                            "law_title": article.get("law_title", ""),
                            "article_display": article.get("article_display", ""),
                        })
                    
                    formatted = _format_tool_result(result)
                    if formatted:
                        all_tool_results.append(formatted)
                
                tool_result_text = "\n\n".join(all_tool_results) if all_tool_results else "未检索到相关法规"
                has_db_results = len(rag_sources) > 0
                
                # 第二轮：带检索结果生成回答
                print(f"[AI Service] 传给第二轮LLM的上下文(前500字): {tool_result_text[:500]}...")
                print(f"[AI Service] 知识库是否有结果: {has_db_results}")
                messages2 = _build_messages_with_context(message, history, tool_result_text, has_results=has_db_results, related_memory=related_memory_context)
                data2 = await _call_llm(
                    api_url, api_key, model, messages2, skip_ssl_verify
                )
                
                # 累计 token 使用
                usage2 = data2.get("usage", {})
                total_usage["prompt_tokens"] += usage2.get("prompt_tokens", 0)
                total_usage["completion_tokens"] += usage2.get("completion_tokens", 0)
                total_usage["total_tokens"] += usage2.get("total_tokens", 0)
                
                reply = data2.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                # AI 直接回答（不需要检索）
                reply = msg.get("content", "")
        else:
            # ========== 普通模式（不使用 Function Calling）==========
            return await _fallback_chat(message, history, db, config, top_k)
        
        return {
            "reply": reply or "抱歉，未能生成回答。",
            "usage": total_usage,
            "provider": provider_id,
            "sources": rag_sources,
        }
        
    except httpx.HTTPStatusError as e:
        error_msg = f"AI 服务请求失败: {e.response.status_code}"
        if e.response.status_code == 401:
            error_msg = "AI 服务认证失败，请检查 API Key 配置"
        elif e.response.status_code == 429:
            error_msg = "AI 服务请求频率过高，请稍后重试"
        raise Exception(error_msg)
    except httpx.TimeoutException:
        raise Exception("AI 服务响应超时，请稍后重试")
    except Exception as e:
        raise Exception(f"AI 服务出错: {str(e)}")


async def _fallback_chat(
    message: str,
    history: Optional[list],
    db: AsyncIOMotorDatabase,
    config: dict,
    top_k: int,
) -> Dict[str, Any]:
    """
    回退模式：使用传统 RAG 方式（适用于不支持 Function Calling 的模型）
    """
    from app.services.knowledge_base_service import KnowledgeBaseService
    
    api_url = config.get("api_url", DEFAULT_API_URL)
    api_key = config.get("api_key", DEFAULT_API_KEY) or ""
    model = config.get("model_name", DEFAULT_MODEL)
    skip_ssl_verify = config.get("skip_ssl_verify", False)
    provider_id = config.get("provider", "default")
    
    rag_context = ""
    rag_sources = []
    
    if db is not None:
        kb_service = KnowledgeBaseService(db)
        rag_data = await kb_service.retrieve(message, top_k=top_k)
        rag_context = rag_data.get("context", "")
        rag_sources = rag_data.get("sources", [])
        direct_answer = rag_data.get("direct_answer", "")
        
        if direct_answer:
            return {
                "reply": direct_answer,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "provider": "knowledge_base",
                "sources": rag_sources,
            }
    
    # 构建消息
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if rag_context:
        messages.append({
            "role": "system",
            "content": f"以下为可引用的法规条文摘要：\n{rag_context}\n\n回答时应优先引用上述条文。"
        })
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    
    data = await _call_llm(api_url, api_key, model, messages, skip_ssl_verify)
    
    reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    
    return {
        "reply": reply or "抱歉，未能生成回答。",
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
        "provider": provider_id,
        "sources": rag_sources,
    }
