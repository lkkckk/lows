from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

law_id = "0ef77c006567da70"
law = db.laws.find_one({"law_id": law_id})

if law:
    print(f"标题: {law['title']}")
    print(f"law_id: {law['law_id']}")
    print(f"分类: {law.get('category', '无')}")
    art_count = db.law_articles.count_documents({"law_id": law_id})
    print(f"条文数: {art_count}")
else:
    print(f"未找到 law_id={law_id} 的法规")

print("\n所有法规:")
for doc in db.laws.find({}, {'title': 1, 'law_id': 1}):
    print(f"  - {doc['title']} ({doc['law_id']})")
