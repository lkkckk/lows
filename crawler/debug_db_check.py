
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env'))

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env'))

mongo_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)

# 修正：连接到后端真正使用的 law_system 数据库
db_name = os.getenv("MONGODB_DB", "law_system")
db = client[db_name]

title = "中华人民共和国治安管理处罚法"

# === 清理逻辑 ===
print(f"🧹 正在从 {db_name} 清理旧数据: {title}...")

# 1. 查 ID (必须在删除前查)
ids_to_clean = [doc['law_id'] for doc in db.laws.find({"title": title})]
print(f"   - 找到旧记录 ID: {ids_to_clean}")

# 2. 删 Laws
result_law = db.laws.delete_many({"title": title})
print(f"   - 删除法规记录: {result_law.deleted_count} 条")

# 3. 删 Articles
if ids_to_clean:
    result_art = db.law_articles.delete_many({"law_id": {"$in": ids_to_clean}})
    print(f"   - 删除关联条文: {result_art.deleted_count} 条")
else:
    print("   - 没有找到旧数据，无需清理条文")

print("✨ 清理完成！请运行 import_local.py")
print("-" * 30)

# === 验证逻辑 (预期应该找不到) ===
law = db.laws.find_one({"title": title})


