"""
批量向量化脚本
为数据库中所有条文生成向量
"""
import asyncio
import os
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8002")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27019")
MONGODB_DB = os.getenv("MONGODB_DB", "law_system")
BATCH_SIZE = 5  # 每批处理的条文数量 (CPU模式下建议调小)


async def get_embeddings(texts: list) -> list:
    """调用向量服务获取文本向量"""
    try:
        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"texts": texts}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embeddings", [])
    except Exception as e:
        print(f"❌ 获取向量失败: {repr(e)}")
        return []


async def check_embedding_service():
    """检查向量服务是否可用"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EMBEDDING_SERVICE_URL}/health")
            if response.status_code == 200:
                print(f"✅ 向量服务可用: {EMBEDDING_SERVICE_URL}")
                return True
    except Exception as e:
        print(f"❌ 向量服务不可用: {e}")
    return False


async def main():
    print("=" * 60)
    print("批量向量化脚本")
    print("=" * 60)
    print(f"向量服务地址: {EMBEDDING_SERVICE_URL}")
    print(f"MongoDB 地址: {MONGODB_URL}")
    print(f"数据库: {MONGODB_DB}")
    print()

    # 1. 检查向量服务
    if not await check_embedding_service():
        print("请先启动向量服务: docker-compose up embedding")
        return

    # 2. 连接数据库
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB]
    articles_collection = db["law_articles"]

    # 3. 统计待处理条文
    total = await articles_collection.count_documents({})
    already_done = await articles_collection.count_documents({"embedding": {"$exists": True}})
    todo = total - already_done

    print(f"📊 条文总数: {total}")
    print(f"📊 已向量化: {already_done}")
    print(f"📊 待处理: {todo}")
    print()

    if todo == 0:
        print("✅ 所有条文已向量化，无需处理")
        return

    # 4. 批量处理
    cursor = articles_collection.find(
        {"embedding": {"$exists": False}},
        {"_id": 1, "content": 1}
    )

    processed = 0
    failed = 0
    batch = []
    batch_ids = []

    async for article in cursor:
        content = article.get("content", "")
        if not content or len(content) < 5:
            continue

        batch.append(content[:2000])  # 限制长度
        batch_ids.append(article["_id"])

        if len(batch) >= BATCH_SIZE:
            # 处理一批
            embeddings = await get_embeddings(batch)
            if embeddings and len(embeddings) == len(batch):
                for i, emb in enumerate(embeddings):
                    await articles_collection.update_one(
                        {"_id": batch_ids[i]},
                        {"$set": {"embedding": emb}}
                    )
                processed += len(batch)
                print(f"✅ 已处理 {processed}/{todo} 条")
            else:
                failed += len(batch)
                print(f"❌ 批次处理失败")

            batch = []
            batch_ids = []

    # 处理最后一批
    if batch:
        embeddings = await get_embeddings(batch)
        if embeddings and len(embeddings) == len(batch):
            for i, emb in enumerate(embeddings):
                await articles_collection.update_one(
                    {"_id": batch_ids[i]},
                    {"$set": {"embedding": emb}}
                )
            processed += len(batch)

    print()
    print("=" * 60)
    print(f"🎉 处理完成！成功: {processed}，失败: {failed}")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
