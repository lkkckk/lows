"""
爬虫数据导入到 MongoDB

使用方法：
    python import_data.py
"""
import json
import sys
from pathlib import Path
from pymongo import MongoClient
from datetime import datetime

import os

# MongoDB 配置
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "law_system")

# 数据文件路径
OUTPUT_DIR = Path("output")
LAWS_FILE = OUTPUT_DIR / "laws.jsonl"
ARTICLES_FILE = OUTPUT_DIR / "law_articles.jsonl"


def import_data():
    """导入数据到 MongoDB"""
    print("🔌 连接 MongoDB...")
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]

    # 清空旧数据（可选）
    print("\n⚠️  是否清空旧数据？(y/n): ", end="")
    if input().lower() == "y":
        print("🗑️  清空旧数据...")
        db.laws.delete_many({})
        db.law_articles.delete_many({})
        print("✅ 旧数据已清空")

    # 导入法规数据
    if LAWS_FILE.exists():
        print(f"\n📥 导入法规数据: {LAWS_FILE}")
        laws_count = 0

        with open(LAWS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    law_data = json.loads(line.strip())

                    # 添加时间戳
                    if "created_at" not in law_data:
                        law_data["created_at"] = datetime.utcnow()

                    # 插入或更新
                    db.laws.update_one(
                        {"law_id": law_data["law_id"]},
                        {"$set": law_data},
                        upsert=True
                    )

                    laws_count += 1

                    if laws_count % 10 == 0:
                        print(f"  已导入 {laws_count} 条法规...")

                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON 解析错误: {e}")
                except Exception as e:
                    print(f"  ❌ 导入错误: {e}")

        print(f"✅ 法规数据导入完成，共 {laws_count} 条")
    else:
        print(f"⚠️  未找到法规数据文件: {LAWS_FILE}")

    # 导入条文数据
    if ARTICLES_FILE.exists():
        print(f"\n📥 导入条文数据: {ARTICLES_FILE}")
        articles_count = 0

        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    article_data = json.loads(line.strip())

                    # 添加时间戳
                    if "created_at" not in article_data:
                        article_data["created_at"] = datetime.utcnow()

                    # 插入或更新
                    db.law_articles.update_one(
                        {
                            "law_id": article_data["law_id"],
                            "article_num": article_data["article_num"]
                        },
                        {"$set": article_data},
                        upsert=True
                    )

                    articles_count += 1

                    if articles_count % 100 == 0:
                        print(f"  已导入 {articles_count} 条条文...")

                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON 解析错误: {e}")
                except Exception as e:
                    print(f"  ❌ 导入错误: {e}")

        print(f"✅ 条文数据导入完成，共 {articles_count} 条")
    else:
        print(f"⚠️  未找到条文数据文件: {ARTICLES_FILE}")

    # 验证导入
    print("\n" + "=" * 60)
    print("📊 数据库统计:")
    print(f"  法规总数: {db.laws.count_documents({})}")
    print(f"  条文总数: {db.law_articles.count_documents({})}")
    print("=" * 60)

    # 创建索引（如果尚未创建）
    print("\n🔍 创建索引...")

    # laws 集合索引
    db.laws.create_index("law_id", unique=True)
    db.laws.create_index([("category", 1), ("level", 1), ("status", 1)])
    db.laws.create_index([("title", "text"), ("summary", "text"), ("full_text", "text")], default_language="none")

    # law_articles 集合索引
    db.law_articles.create_index([("law_id", 1), ("article_num", 1)], unique=True)
    db.law_articles.create_index("law_id")
    db.law_articles.create_index([("content", "text"), ("article_display", "text")], default_language="none")

    print("✅ 索引创建完成")

    client.close()
    print("\n🎉 数据导入完成！")


if __name__ == "__main__":
    try:
        import_data()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        sys.exit(1)
