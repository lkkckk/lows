"""
Embedding 服务客户端
用于调用本地 embedding-service 获取文本向量
"""
import httpx
import os
from typing import List, Optional

# 从环境变量读取配置，默认使用 Docker 网络内的服务名
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding:8000")

async def get_embedding(text: str) -> Optional[List[float]]:
    """获取单个文本的向量"""
    result = await get_embeddings([text])
    return result[0] if result else None

async def get_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """批量获取文本向量"""
    if not texts:
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"texts": texts}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embeddings", [])
    except httpx.ConnectError:
        print(f"[Embedding Client] ❌ 无法连接到向量服务: {EMBEDDING_SERVICE_URL}")
        return None
    except httpx.TimeoutException:
        print(f"[Embedding Client] ❌ 向量服务响应超时")
        return None
    except Exception as e:
        print(f"[Embedding Client] ❌ 调用失败: {e}")
        return None

async def check_health() -> bool:
    """检查向量服务是否可用"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EMBEDDING_SERVICE_URL}/health")
            return response.status_code == 200
    except Exception:
        return False
