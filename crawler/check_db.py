from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

print("法规列表:")
for doc in db.laws.find({}, {'title': 1, 'law_id': 1}):
    art_count = db.law_articles.count_documents({'law_id': doc['law_id']})
    print(f"  - {doc['title']} (条文: {art_count})")
