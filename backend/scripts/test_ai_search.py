"""
测试脚本：直接测试 AI Service 的检索逻辑
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["law_system"]
    
    # 模拟 execute_search_legal_knowledge 的逻辑
    search_law_name = "治安管理处罚法"
    laws_collection = db["laws"]
    articles_collection = db["law_articles"]
    
    print(f"正在检索: '{search_law_name}'")
    
    # 按法律标题匹配
    law_name_pattern = search_law_name.replace("中华人民共和国", "").strip()
    law_regex = {"title": {"$regex": law_name_pattern, "$options": "i"}}
    
    matching_laws = await laws_collection.find(
        law_regex, {"law_id": 1, "title": 1}
    ).to_list(length=10)
    
    if matching_laws:
        print(f"匹配到 {len(matching_laws)} 部法律:")
        for law in matching_laws:
            print(f"  - {law['title']} (law_id: {law['law_id']})")
        
        # 取匹配到的法律的 law_id
        law_ids = [law["law_id"] for law in matching_laws]
        
        # 查询这些法律的条文
        article_query = {"law_id": {"$in": law_ids}}
        articles = await articles_collection.find(article_query).sort("article_num", 1).limit(6).to_list(length=6)
        
        print(f"\n找到 {len(articles)} 条条文（前6条）:")
        for article in articles:
            print(f"  - {article.get('article_display')}: {article.get('content', '')[:50]}...")
    else:
        print("未匹配到任何法律")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
