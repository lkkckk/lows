from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['law_system']

# 查找"公安机关办理行政案件程序规定"
law = db.laws.find_one({"title": {"$regex": "行政案件程序规定"}})

if law:
    print("=" * 60)
    print(f"标题: {law.get('title')}")
    print(f"law_id: {law.get('law_id')}")
    print("-" * 40)
    print(f"issue_org: {law.get('issue_org', '【未设置】')}")
    print(f"issue_date: {law.get('issue_date', '【未设置】')}")
    print(f"effect_date: {law.get('effect_date', '【未设置】')}")
    print(f"category: {law.get('category', '【未设置】')}")
    print(f"level: {law.get('level', '【未设置】')}")
    print(f"status: {law.get('status', '【未设置】')}")
    print("=" * 60)
    print("\n所有字段名:")
    for key in law.keys():
        print(f"  - {key}")
else:
    print("未找到该法规")
