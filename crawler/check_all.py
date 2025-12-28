from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

# 查找所有包含"刑事案件程序规定"的法规
laws = list(db.laws.find({"title": {"$regex": "刑事案件程序规定"}}))

print(f"找到 {len(laws)} 条记录：\n")
for law in laws:
    print(f"标题: {law.get('title')}")
    print(f"  law_id: {law.get('law_id')}")
    print(f"  issue_org: {law.get('issue_org')}")
    print(f"  issue_date: {law.get('issue_date')}")
    print(f"  effect_date: {law.get('effect_date')}")
    print()
