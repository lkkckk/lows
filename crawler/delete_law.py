from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

law_id = "0ef77c006567da70"
law = db.laws.find_one({"law_id": law_id})

if law:
    # 删除条文
    art_result = db.law_articles.delete_many({"law_id": law_id})
    # 删除法规
    law_result = db.laws.delete_one({"law_id": law_id})
    print(f"✅ 已删除法规: {law['title']}")
    print(f"   - 删除法规记录: {law_result.deleted_count} 条")
    print(f"   - 删除关联条文: {art_result.deleted_count} 条")
else:
    print(f"未找到 law_id={law_id} 的法规")

print("\n当前法规列表:")
for doc in db.laws.find({}, {'title': 1}):
    print(f"  - {doc['title']}")
