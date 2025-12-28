import httpx
from bs4 import BeautifulSoup
import urllib.parse
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

keyword = "中华人民共和国刑法"
search_url = f"https://www.law-star.com/search?keyword={urllib.parse.quote(keyword)}"

with httpx.Client(headers=headers, follow_redirects=True, http2=True) as client:
    # First visit homepage to get cookies
    client.get("https://www.law-star.com/")
    time.sleep(1)
    
    # Then search
    resp = client.get(search_url)
    print(f"Status: {resp.status_code}")
    print(f"Content Length: {len(resp.text)}")
    
    soup = BeautifulSoup(resp.text, 'lxml')
    links = soup.select('a')
    print(f"Total links found: {len(links)}")
    for link in links[:10]:
        print(f"Link: {link.get_text().strip()} -> {link.get('href')}")
        
    if "访问受限" in resp.text:
        print("Blocked: 访问受限")
    elif "验证码" in resp.text:
        print("Blocked: 验证码")
