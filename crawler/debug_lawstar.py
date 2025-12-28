import httpx
from bs4 import BeautifulSoup
import urllib.parse

url = "https://www.law-star.com/search?keyword=" + urllib.parse.quote("中华人民共和国刑法")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

with httpx.Client(headers=headers, follow_redirects=True) as client:
    resp = client.get(url)
    print(f"Status: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'lxml')
    links = soup.select('a')
    print(f"Total links found: {len(links)}")
    for link in links[:20]:
        print(f"Link: {link.get_text().strip()} -> {link.get('href')}")
    
    # Check for title class
    titles = soup.select('.title')
    print(f"Found {len(titles)} elements with class 'title'")
