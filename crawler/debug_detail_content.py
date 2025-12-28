import httpx
from bs4 import BeautifulSoup
import urllib.parse

# 治安管理处罚法的一个详情页
url = "https://www.law-star.com/detail?rjs8=ABF317AE13C5B54A9946CD8A3B0DA513"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

with httpx.Client(headers=headers, follow_redirects=True) as client:
    resp = client.get(url)
    print(f"Status: {resp.status_code}")
    print(f"Is '治安管理' in text? : {'治安管理' in resp.text}")
    print(f"Sample text snippet: {resp.text[500:1500]}")
