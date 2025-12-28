from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

# 查找搜索"26"时匹配的条文
articles = list(db.law_articles.find({
    'law_id': 'be642b969d59b340', 
    'content': {'$regex': '26'}
}).sort('article_num', 1).limit(5))

print(f'匹配到 {len(articles)} 条')
for a in articles:
    print(f"article_num={a.get('article_num')}, display={a.get('article_display')}")
    print(f"  内容前100字: {a.get('content', '')[:100]}")
    print()

# 同时检查第26条的实际article_num
a26 = db.law_articles.find_one({
    'law_id': 'be642b969d59b340',
    'article_display': {'$regex': '^第二十六条'}
})
if a26:
    print(f"第二十六条的article_num = {a26.get('article_num')}")
else:
    print("未找到第二十六条")
