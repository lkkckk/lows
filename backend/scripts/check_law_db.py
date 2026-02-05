"""
测试脚本：检查数据库中治安管理处罚法的数据
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    # 优先使用环境变量，否则使用 Docker 网络的 mongodb 主机名
    mongo_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["law_system"]  # 正确的数据库名
    
    # 1. 检查 laws 集合中是否有治安管理处罚法
    print("=" * 50)
    print("1. 检查 laws 集合中的治安管理处罚法")
    print("=" * 50)
    
    laws = await db.laws.find(
        {"title": {"$regex": "治安管理处罚", "$options": "i"}},
        {"law_id": 1, "title": 1}
    ).to_list(length=10)
    
    if laws:
        for law in laws:
            print(f"  - law_id: {law['law_id']}, title: {law['title']}")
    else:
        print("  未找到任何治安管理处罚法相关法律！")
    
    # 2. 检查 law_articles 集合中是否有对应条文
    print("\n" + "=" * 50)
    print("2. 检查 law_articles 集合中的条文")
    print("=" * 50)
    
    if laws:
        law_ids = [law["law_id"] for law in laws]
        articles = await db.law_articles.find(
            {"law_id": {"$in": law_ids}},
            {"law_id": 1, "article_display": 1, "content": 1}
        ).sort("article_num", 1).limit(5).to_list(length=5)
        
        print(f"  找到 {len(articles)} 条条文（显示前5条）：")
        for article in articles:
            content_preview = article.get("content", "")[:100]
            print(f"  - {article.get('article_display')}: {content_preview}...")
    
    # 3. 检查赌博相关条文
    print("\n" + "=" * 50)
    print("3. 检查赌博相关条文")
    print("=" * 50)
    
    gambling_articles = await db.law_articles.find(
        {"content": {"$regex": "赌博", "$options": "i"}},
        {"law_id": 1, "article_display": 1, "content": 1}
    ).limit(5).to_list(length=5)
    
    if gambling_articles:
        # 获取对应法律标题
        law_ids = list({a["law_id"] for a in gambling_articles})
        laws_map = {}
        laws_data = await db.laws.find({"law_id": {"$in": law_ids}}).to_list(length=10)
        for law in laws_data:
            laws_map[law["law_id"]] = law["title"]
        
        for article in gambling_articles:
            law_title = laws_map.get(article["law_id"], "未知")
            content_preview = article.get("content", "")[:150]
            print(f"\n  《{law_title}》{article.get('article_display')}：")
            print(f"    {content_preview}...")
    else:
        print("  未找到任何赌博相关条文！")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
