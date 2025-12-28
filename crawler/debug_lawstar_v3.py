import httpx
from bs4 import BeautifulSoup
import urllib.parse
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

keyword = "中华人民共和国刑法"
search_url = f"https://www.law-star.com/search?keyword={urllib.parse.quote(keyword)}"

with httpx.Client(headers=headers, follow_redirects=True) as client:
    resp = client.get(search_url)
    print(resp.text[:2000])
