"""
示例爬虫：中国政府法制信息网适配器

【TODO】您需要根据实际目标网站调整：
1. extract_law_links() 中的选择器
2. parse_law_page() 中的数据提取逻辑
3. 列表页 URL 格式

当前实现为示例骨架，展示如何使用 BaseLawSpider。
"""
from base_spider import BaseLawSpider
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
import re


class ChinaLawSpider(BaseLawSpider):
    """中国政府法制信息网爬虫（示例）"""

    def __init__(self):
        super().__init__(
            name="china_law",
            base_url="https://flk.npc.gov.cn",  # 示例 URL（请替换为实际网站）
            output_dir="output",
            delay=2.0,  # 请求延迟 2 秒
        )

    def extract_law_links(self, list_page_url: str) -> List[str]:
        """
        从列表页提取法规链接

        【TODO】请根据实际网站结构调整选择器
        """
        html = self._fetch_page(list_page_url)
        soup = BeautifulSoup(html, "lxml")

        law_urls = []

        # 示例选择器（需根据实际网站调整）
        # 假设法规链接在 <a class="law-title"> 标签中
        for link in soup.select("a.law-title"):  # ⚠️ TODO: 调整选择器
            href = link.get("href")
            if href:
                # 处理相对路径
                if href.startswith("/"):
                    full_url = self.base_url + href
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = self.base_url + "/" + href

                law_urls.append(full_url)

        return law_urls

    def parse_law_page(self, url: str, html: str) -> Optional[Dict]:
        """
        解析法规详情页

        【TODO】请根据实际网站结构调整数据提取逻辑
        """
        soup = BeautifulSoup(html, "lxml")

        try:
            # 提取标题（示例选择器）
            title_elem = soup.select_one("h1.law-title")  # ⚠️ TODO: 调整选择器
            if not title_elem:
                return None
            title = self._clean_text(title_elem.get_text())

            # 提取元信息（示例）
            meta_info = self._extract_meta_info(soup)

            # 提取全文（示例选择器）
            content_elem = soup.select_one("div.law-content")  # ⚠️ TODO: 调整选择器
            if not content_elem:
                return None
            full_text = self._clean_text(content_elem.get_text())

            # 拆分条文
            articles = self._split_articles(full_text)

            # 生成法规 ID
            law_id = self._generate_law_id(title, meta_info.get("issue_date", ""))

            return {
                "law_id": law_id,
                "title": title,
                "category": meta_info.get("category", "未分类"),
                "level": meta_info.get("level", "其他"),
                "issue_org": meta_info.get("issue_org", ""),
                "issue_date": meta_info.get("issue_date", ""),
                "effect_date": meta_info.get("effect_date", ""),
                "status": meta_info.get("status", "有效"),
                "summary": meta_info.get("summary", ""),
                "tags": meta_info.get("tags", []),
                "source_url": url,
                "full_text": full_text,
                "articles": articles,
            }

        except Exception as e:
            print(f"解析失败: {url} - {e}")
            return None

    def _extract_meta_info(self, soup: BeautifulSoup) -> Dict:
        """
        提取元信息

        【TODO】根据实际网站结构调整
        """
        meta_info = {}

        # 示例：假设元信息在 <dl class="meta"> 中
        meta_elem = soup.select_one("dl.meta")  # ⚠️ TODO: 调整选择器

        if meta_elem:
            # 提取键值对（示例：<dt>制定机关</dt><dd>全国人大</dd>）
            dt_list = meta_elem.select("dt")
            dd_list = meta_elem.select("dd")

            for dt, dd in zip(dt_list, dd_list):
                key = self._clean_text(dt.get_text())
                value = self._clean_text(dd.get_text())

                # 映射字段名
                if "制定机关" in key or "制定机关" in key:
                    meta_info["issue_org"] = value
                elif "发布日期" in key or "公布日期" in key:
                    meta_info["issue_date"] = value
                elif "生效日期" in key or "施行日期" in key:
                    meta_info["effect_date"] = value
                elif "效力层级" in key:
                    meta_info["level"] = value
                elif "分类" in key:
                    meta_info["category"] = value
                elif "状态" in key or "效力" in key:
                    meta_info["status"] = value

        # 默认值
        meta_info.setdefault("category", "综合")
        meta_info.setdefault("level", "其他")
        meta_info.setdefault("issue_org", "")
        meta_info.setdefault("issue_date", "")
        meta_info.setdefault("effect_date", "")
        meta_info.setdefault("status", "有效")

        return meta_info


# 运行示例
if __name__ == "__main__":
    print("=" * 60)
    print("⚠️  这是一个示例爬虫，您需要根据实际目标网站调整代码")
    print("=" * 60)
    print("\n请按以下步骤操作：")
    print("1. 在浏览器中打开目标法规网站")
    print("2. 使用开发者工具（F12）检查页面结构")
    print("3. 找到法规列表的选择器（extract_law_links 方法）")
    print("4. 找到法规详情的选择器（parse_law_page 方法）")
    print("5. 修改本文件中标记为 TODO 的部分")
    print("6. 取消下面的注释并运行\n")

    # TODO: 取消注释并填入实际的列表页 URL
    # spider = ChinaLawSpider()
    # spider.run([
    #     "https://flk.npc.gov.cn/xingshi.html",  # 示例：刑事法律列表页
    #     "https://flk.npc.gov.cn/xingzheng.html",  # 示例：行政法律列表页
    # ])

    print("✅ 示例文件已准备好，请根据实际网站调整后运行")
