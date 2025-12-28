import httpx
import asyncio
from bs4 import BeautifulSoup
import re
from base_spider import BaseLawSpider
import urllib.parse
import logging

class LawStarSpider(BaseLawSpider):
    def __init__(self, db_client=None):
        super().__init__(name="law_star", base_url="https://www.law-star.com")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.law-star.com/"
        }
        self.logger = logging.getLogger("LawStarSpider")
        logging.basicConfig(level=logging.INFO)

    async def search_and_parse(self, law_title):
        """根据标题搜索并解析法规"""
        # 如果标题带括号如 (2012-10-26 实施)，剥离出来作为检索词
        search_keyword = re.sub(r'\(.*?\)', '', law_title).strip()
        self.logger.info(f"正在自 Law-Star 检索: {search_keyword}")
        
        search_url = f"{self.base_url}/search?keyword={urllib.parse.quote(search_keyword)}"
        try:
          async with httpx.AsyncClient(headers=self.headers, timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(search_url)
            if resp.status_code != 200:
                self.logger.error(f"搜索请求失败: {resp.status_code}")
                return None
            
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # 找到搜出的结果
            # 调研结果显示：.title a[href^="/detail"]
            first_link = None
            links = soup.select('.title a[href^="/detail"]')
            
            if not links:
                # 兜底选择器
                links = soup.select('a[href^="/detail"]')
                
            for link_el in links:
                link_text = link_el.get_text().strip()
                # 如果是治安管理处罚法且带日期，我们需要找到最匹配的那个
                # 现简化为：如果是搜索关键词的一部分，就选第一个（通常是最新的）
                if search_keyword in link_text:
                    first_link = link_el['href']
                    break
            
            if not first_link:
                self.logger.warning(f"未能找到匹配的法规: {search_keyword}")
                return None
            
            if first_link.startswith("/"):
                detail_url = self.base_url + first_link
            elif not first_link.startswith("http"):
                detail_url = self.base_url + "/" + first_link
            else:
                detail_url = first_link
                
            return await self.parse_detail_page(detail_url, law_title)
        except Exception as e:
            self.logger.error(f"处理 {law_title} 时发生异常: {str(e)}")
            return None

    async def parse_detail_page(self, url, law_title):
        """解析详情页内容"""
        self.logger.info(f"正在抓取详情页: {url}")
        
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
            # 处理编码问题
            if "charset=gb2312" in resp.text.lower() or "charset=gbk" in resp.text.lower():
                resp.encoding = "gbk"
            else:
                resp.encoding = "utf-8"
                
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # 1. 提取元数据
            def get_meta_value(label):
                # Law-star 详情页可能会在表格或 div 中显示元数据
                el = soup.find(lambda t: t.name in ["span", "div", "li", "td"] and label in t.text)
                if el:
                    text = el.get_text().strip()
                    if label in text:
                        return text.split(label)[-1].strip()
                return ""

            # 抓取页面上的真实标题
            real_title = soup.select_one("h1, .head h1")
            actual_title = real_title.get_text().strip() if real_title else law_title

            issue_date = get_meta_value("发布日期：") or get_meta_value("发布日期:")
            metadata = {
                "title": actual_title,
                "issue_org": get_meta_value("发布部门：") or get_meta_value("发布部门:"),
                "issue_date": issue_date,
                "effect_date": get_meta_value("实施日期：") or get_meta_value("实施日期:"),
                "status": get_meta_value("时效性：") or get_meta_value("时效性:") or "有效",
                "level": get_meta_value("效力级别：") or get_meta_value("效力级别:") or "法律",
                "category": get_meta_value("类别：") or get_meta_value("类别:") or "通用",
                "source_url": url
            }
            
            # 使用基类方法生成 ID
            metadata["law_id"] = self._generate_law_id(actual_title, issue_date or "unknown")

            # 2. 提取全文内容
            # Law-Star 正文通常在 id 为 content 的 div 或 .scroll 中
            content_div = soup.select_one("#content, .scroll, .scrollable, .head + div")
            if not content_div:
                # 按照段落抓取
                content_text = "\n".join([p.get_text() for p in soup.select(".row, p") if len(p.get_text()) > 5])
            else:
                content_text = content_div.get_text("\n")

            if not content_text or len(content_text) < 50:
                self.logger.error("抓取到的正文内容过短")
                return None

            # 3. 拆分条文
            articles = self._split_articles(content_text)
            
            if not articles:
                self.logger.warning(f"未能拆分出条目，整篇存入第一条")
                articles = [{
                    "article_num": 1,
                    "article_display": "全文",
                    "content": content_text,
                    "keywords": self._extract_keywords(content_text)
                }]
            
            # 4. 保存为标准格式
            law_data = metadata.copy()
            law_data["articles"] = articles
            self._save_to_jsonl(law_data)
            
            self.logger.info(f"法规 {actual_title} 处理完成，共 {len(articles)} 条")
            return law_data
