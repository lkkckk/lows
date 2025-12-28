from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

law = db.laws.find_one({'title': '中华人民共和国刑法（2023年修正）'})
if law:
    print(f"法规标题: {law['title']}")
    print(f"law_id: {law['law_id']}")
    print(f"摘要: {law.get('summary', '无')[:100] if law.get('summary') else '无'}")
    
    art_count = db.law_articles.count_documents({'law_id': law['law_id']})
    print(f"条文数量: {art_count}")
    
    print("\n前5条条文:")
    for art in db.law_articles.find({'law_id': law['law_id']}).sort('article_num', 1).limit(5):
        content_preview = art['content'][:60].replace('\n', ' ')
        print(f"  {art['article_display']} ({art.get('chapter', '')}): {content_preview}...")
else:
    print("未找到刑法")
