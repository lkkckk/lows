"""
MongoDB 数据库连接配置
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import os

# 数据库配置
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "law_system")

# 异步客户端（用于 FastAPI）
async_client: Optional[AsyncIOMotorClient] = None
async_db = None

# 同步客户端（用于初始化脚本）
sync_client: Optional[MongoClient] = None
sync_db = None


async def connect_to_mongo():
    """连接到 MongoDB（异步）"""
    global async_client, async_db
    async_client = AsyncIOMotorClient(MONGODB_URL)
    async_db = async_client[MONGODB_DB]
    print(f"✅ 已连接到 MongoDB: {MONGODB_URL}/{MONGODB_DB}")


async def close_mongo_connection():
    """关闭 MongoDB 连接（异步）"""
    global async_client
    if async_client:
        async_client.close()
        print("🔌 已关闭 MongoDB 连接")


def get_database():
    """获取异步数据库对象（用于 API 路由）"""
    global async_db
    return async_db


def get_sync_db():
    """获取同步数据库连接（用于脚本）"""
    global sync_client, sync_db
    if not sync_client:
        sync_client = MongoClient(MONGODB_URL)
        sync_db = sync_client[MONGODB_DB]
    return sync_db


# 集合名称常量
COLLECTION_LAWS = "laws"
COLLECTION_LAW_ARTICLES = "law_articles"
COLLECTION_DOC_TEMPLATES = "doc_templates"
COLLECTION_DOC_INSTANCES = "doc_instances"
COLLECTION_CASES = "cases"
COLLECTION_TRANSCRIPTS = "transcripts"
