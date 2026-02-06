"""
验证向量搜索效果
"""
import asyncio
import os
from pprint import pprint
# 设置环境变量以启用向量搜索
os.environ["VECTOR_SEARCH_ENABLED"] = "true"
os.environ["EMBEDDING_SERVICE_URL"] = "http://law_system_embedding:8000"

from app.services.law_service import LawService
from motor.motor_asyncio import AsyncIOMotorClient

async def test_search():
    # 连接数据库
    client = AsyncIOMotorClient("mongodb://mongodb:27017")
    db = client["law_system"]
    law_service = LawService(db)
    
    test_cases = [
        "吸毒",          # 预期匹配：吸食、注射毒品
        "醉驾",          # 预期匹配：醉酒驾驶
        "偷东西",        # 预期匹配：盗窃
        "打人",          # 预期匹配：殴打他人
        "喝多了开车怎么判" # 复杂语义
    ]
    
    print("="*60)
    print("🚀 开始向量语义搜索测试")
    print("="*60)
    
    for query in test_cases:
        print(f"\n🔎 搜索词: [{query}]")
        try:
            results = await law_service.vector_search_for_rag(query, top_k=3)
            if results:
                for i, r in enumerate(results):
                    print(f"   {i+1}. [{r['similarity']:.4f}] {r['law_title']} {r['article_display']}")
                    print(f"      {r['content'][:100]}...")
            else:
                print("   ❌ 未找到结果")
        except Exception as e:
            print(f"   ❌ 搜索出错: {e}")

if __name__ == "__main__":
    import sys
    # 添加项目根目录到 python path
    sys.path.append(os.getcwd())
    asyncio.run(test_search())
