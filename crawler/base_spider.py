"""
法规爬虫基类（适配器模式）

使用说明：
1. 继承 BaseLawSpider 类
2. 实现 extract_law_links() 和 parse_law_page() 方法
3. 运行 run() 方法开始爬取
"""
import httpx
import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import re


class BaseLawSpider:
    """法规爬虫基类"""

    def __init__(
        self,
        name: str,
        base_url: str,
        output_dir: str = "output",
        delay: float = 1.0,
    ):
        """
        初始化爬虫

        Args:
            name: 爬虫名称
            base_url: 目标网站基础 URL
            output_dir: 输出目录
            delay: 请求延迟（秒）
        """
        self.name = name
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.delay = delay

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 已爬取 URL 集合（去重）
        self.seen_urls: Set[str] = self._load_seen_urls()

        # HTTP 客户端
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            follow_redirects=True,
        )

        # 统计信息
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

    def _load_seen_urls(self) -> Set[str]:
        """加载已爬取的 URL 集合"""
        seen_file = self.output_dir / f"{self.name}_seen_urls.txt"
        if seen_file.exists():
            with open(seen_file, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f)
        return set()

    def _save_seen_url(self, url: str):
        """保存已爬取的 URL"""
        seen_file = self.output_dir / f"{self.name}_seen_urls.txt"
        with open(seen_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")
        self.seen_urls.add(url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _fetch_page(self, url: str) -> str:
        """
        获取页面 HTML（带重试）

        Args:
            url: 目标 URL

        Returns:
            HTML 内容
        """
        print(f"📥 正在获取: {url}")
        response = self.client.get(url)
        response.raise_for_status()
        time.sleep(self.delay)  # 限速
        return response.text

    def extract_law_links(self, list_page_url: str) -> List[str]:
        """
        从列表页提取法规链接（需子类实现）

        Args:
            list_page_url: 列表页 URL

        Returns:
            法规详情页 URL 列表
        """
        raise NotImplementedError("子类必须实现 extract_law_links() 方法")

    def parse_law_page(self, url: str, html: str) -> Optional[Dict]:
        """
        解析法规详情页（需子类实现）

        Args:
            url: 法规详情页 URL
            html: 页面 HTML

        Returns:
            法规数据字典，包含以下键：
            - law_id: 法规唯一标识
            - title: 法规标题
            - category: 法规分类
            - level: 效力层级
            - issue_org: 制定机关
            - issue_date: 发布日期
            - effect_date: 生效日期
            - status: 效力状态
            - summary: 摘要
            - tags: 标签列表
            - full_text: 法规全文
            - articles: 条文列表（每个条文包含 article_num, article_display, content, chapter, section, keywords）
        """
        raise NotImplementedError("子类必须实现 parse_law_page() 方法")

    def _clean_text(self, text: str) -> str:
        """
        清洗文本
        Args:
            text: 原始文本
        Returns:
            清洗后的文本
        """
        # 1. 替换水平空白符（空格、tab）为单个空格，但保留换行符
        text = re.sub(r'[ \t\r\f\v]+', ' ', text)
        
        # 2. 规范化换行符
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def _split_articles(self, full_text: str) -> List[Dict]:
        """
        拆分条文（通用实现，子类可覆盖）

        Args:
            full_text: 法规全文

        Returns:
            条文列表
        """
        articles = []

        # 匹配条文（示例：第一条、第二条、第123条）
        pattern = r'第([零一二三四五六七八九十百千]+|[0-9]+)条'
        matches = list(re.finditer(pattern, full_text))

        for i, match in enumerate(matches):
            article_display = match.group(0)
            article_num = self._parse_article_num(match.group(1))

            # 提取条文内容（从当前条号到下一个条号之间的文本）
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            content = self._clean_text(full_text[start:end])

            articles.append({
                "article_num": article_num,
                "article_display": article_display,
                "content": content,
                "keywords": self._extract_keywords(content),
            })

        return articles

    def _parse_article_num(self, num_str: str) -> int:
        """
        解析条号（中文数字转阿拉伯数字）

        Args:
            num_str: 数字字符串（可能是中文或阿拉伯数字）

        Returns:
            阿拉伯数字
        """
        # 如果已经是阿拉伯数字，直接返回
        if num_str.isdigit():
            return int(num_str)

        # 中文数字转换
        chinese_num_map = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000
        }

        # 特殊处理"十"开头的情况
        if num_str.startswith('十'):
            num_str = '一' + num_str

        result = 0
        temp = 0
        unit = 1

        for char in reversed(num_str):
            num = chinese_num_map.get(char, 0)

            if num >= 10:
                if num > unit:
                    unit = num
                else:
                    unit *= num

                if temp == 0:
                    temp = unit
            else:
                temp = num * unit

            result += temp
            temp = 0

        return result

    def _extract_keywords(self, content: str, top_n: int = 10) -> List[str]:
        """
        简单关键词提取（基于长度和频率）

        Args:
            content: 条文内容
            top_n: 返回前 N 个关键词

        Returns:
            关键词列表
        """
        # 简单实现：提取 2-4 字的词汇
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)

        # 统计词频
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 按频率排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        return [word for word, _ in sorted_words[:top_n]]

    def _generate_law_id(self, title: str, issue_date: str) -> str:
        """
        生成法规唯一标识

        Args:
            title: 法规标题
            issue_date: 发布日期

        Returns:
            法规 ID
        """
        # 使用标题和日期生成唯一 ID
        raw = f"{title}_{issue_date}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _save_to_jsonl(self, law_data: Dict):
        """
        保存法规数据到 JSONL 文件

        Args:
            law_data: 法规数据
        """
        # 保存法规元信息
        laws_file = self.output_dir / "laws.jsonl"
        law_info = {k: v for k, v in law_data.items() if k != "articles"}
        with open(laws_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(law_info, ensure_ascii=False) + "\n")

        # 保存条文
        articles_file = self.output_dir / "law_articles.jsonl"
        for article in law_data.get("articles", []):
            article_data = {
                "law_id": law_data["law_id"],
                "article_num": article["article_num"],
                "article_display": article["article_display"],
                "content": article["content"],
                "chapter": article.get("chapter"),
                "section": article.get("section"),
                "keywords": article.get("keywords", []),
            }
            with open(articles_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(article_data, ensure_ascii=False) + "\n")

    def run(self, list_page_urls: List[str]):
        """
        运行爬虫

        Args:
            list_page_urls: 列表页 URL 列表
        """
        print(f"🚀 启动爬虫: {self.name}")
        print(f"📁 输出目录: {self.output_dir}")

        all_law_urls = []

        # 步骤1: 提取所有法规链接
        for list_url in list_page_urls:
            try:
                law_urls = self.extract_law_links(list_url)
                all_law_urls.extend(law_urls)
                print(f"✅ 从 {list_url} 提取到 {len(law_urls)} 个法规链接")
            except Exception as e:
                print(f"❌ 提取链接失败 {list_url}: {e}")

        print(f"\n📊 总共发现 {len(all_law_urls)} 个法规链接")

        # 步骤2: 爬取每个法规
        for i, url in enumerate(all_law_urls, 1):
            self.stats["total"] += 1

            # 去重检查
            if url in self.seen_urls:
                print(f"⏭️  [{i}/{len(all_law_urls)}] 已爬取，跳过: {url}")
                self.stats["skipped"] += 1
                continue

            try:
                # 获取页面
                html = self._fetch_page(url)

                # 解析数据
                law_data = self.parse_law_page(url, html)

                if law_data:
                    # 保存数据
                    self._save_to_jsonl(law_data)
                    self._save_seen_url(url)

                    self.stats["success"] += 1
                    print(f"✅ [{i}/{len(all_law_urls)}] 成功: {law_data['title']}")
                else:
                    self.stats["failed"] += 1
                    print(f"❌ [{i}/{len(all_law_urls)}] 解析失败: {url}")

            except Exception as e:
                self.stats["failed"] += 1
                print(f"❌ [{i}/{len(all_law_urls)}] 错误: {url} - {e}")

        # 打印统计
        print("\n" + "=" * 60)
        print("📈 爬取统计:")
        print(f"  总计: {self.stats['total']}")
        print(f"  成功: {self.stats['success']}")
        print(f"  失败: {self.stats['failed']}")
        print(f"  跳过: {self.stats['skipped']}")
        print("=" * 60)

        self.client.close()
