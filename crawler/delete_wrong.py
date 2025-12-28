from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

# 删除错误的记录
wrong_title = "第一编  总则"
law = db.laws.find_one({"title": wrong_title})

if law:
    law_id = law['law_id']
    # 删除条文
    art_result = db.law_articles.delete_many({"law_id": law_id})
    # 删除法规
    law_result = db.laws.delete_one({"law_id": law_id})
    print(f"✅ 已删除法规: {wrong_title}")
    print(f"   - 删除法规记录: {law_result.deleted_count} 条")
    print(f"   - 删除关联条文: {art_result.deleted_count} 条")
else:
    print(f"未找到标题为 '{wrong_title}' 的法规")

# 显示当前法规列表
print("\n当前法规列表:")
for doc in db.laws.find({}, {'title': 1}):
    print(f"  - {doc['title']}")
