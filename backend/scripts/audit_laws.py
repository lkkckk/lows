"""
审计脚本：检查数据库中所有法律法规，分析检索覆盖范围
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["law_system"]
    
    # 1. 统计法规总览
    print("=" * 60)
    print("1. 法规数据库总览")
    print("=" * 60)
    
    laws_count = await db.laws.count_documents({})
    articles_count = await db.law_articles.count_documents({})
    print(f"  法规总数: {laws_count}")
    print(f"  条文总数: {articles_count}")
    
    # 2. 列出所有法规名称
    print("\n" + "=" * 60)
    print("2. 所有法规列表")
    print("=" * 60)
    
    laws = await db.laws.find({}, {"title": 1, "category": 1}).to_list(length=100)
    for i, law in enumerate(laws, 1):
        print(f"  {i}. [{law.get('category', '未分类')}] {law['title']}")
    
    # 3. 检查是否有多版本法规
    print("\n" + "=" * 60)
    print("3. 多版本法规检测")
    print("=" * 60)
    
    import re
    base_names = {}
    for law in laws:
        title = law["title"]
        # 去掉年份后缀
        year_pattern = r'[（\(]\d{4}年[修订正]+[）\)]'
        base_name = re.sub(year_pattern, '', title).strip()
        if base_name not in base_names:
            base_names[base_name] = []
        base_names[base_name].append(title)
    
    multi_version = {k: v for k, v in base_names.items() if len(v) > 1}
    if multi_version:
        for base, versions in multi_version.items():
            print(f"  {base}:")
            for v in versions:
                print(f"    - {v}")
    else:
        print("  无多版本法规")
    
    # 4. 检查常见违法行为关键词覆盖
    print("\n" + "=" * 60)
    print("4. 常见违法行为关键词覆盖检测")
    print("=" * 60)
    
    keywords = ["赌博", "卖淫", "嫖娼", "盗窃", "抢劫", "诈骗", "吸毒", "贩毒", 
                "酒驾", "醉驾", "斗殴", "寻衅滋事", "故意伤害", "敲诈勒索"]
    
    for kw in keywords:
        count = await db.law_articles.count_documents(
            {"content": {"$regex": kw, "$options": "i"}}
        )
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {kw}: {count} 条条文")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
