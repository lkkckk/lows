"""
修复条文内容中重复的"第X条"前缀

问题描述：
- 脚本导入的法规条文，content字段开头包含"第X条"
- 而前端显示时会从article_display字段单独提取"第X条"显示在上方
- 导致"第X条"重复显示

解决方案：
- 遍历所有law_articles文档
- 如果content以"第X条"开头，则移除该前缀
"""
import os
import re
from pymongo import MongoClient

# MongoDB 配置
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27019")
MONGODB_DB = os.getenv("MONGODB_DB", "law_system")

# 匹配"第X条"的正则表达式（支持中文数字和阿拉伯数字）
ARTICLE_PREFIX_PATTERN = re.compile(
    r'^(第[一二三四五六七八九十百千零〇\d]+条)\s*'
)


def fix_duplicate_prefix():
    """修复条文内容中重复的第X条前缀"""
    print("🔌 连接 MongoDB...")
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]
    collection = db.law_articles
    
    # 统计
    total_count = collection.count_documents({})
    fixed_count = 0
    skipped_count = 0
    
    print(f"📊 共有 {total_count} 条条文记录")
    print("🔍 开始扫描并修复...\n")
    
    # 遍历所有条文
    cursor = collection.find({}, {"_id": 1, "article_display": 1, "content": 1})
    
    for doc in cursor:
        content = doc.get("content", "")
        article_display = doc.get("article_display", "")
        
        if not content:
            skipped_count += 1
            continue
        
        # 检查content是否以"第X条"开头
        match = ARTICLE_PREFIX_PATTERN.match(content)
        
        if match:
            prefix = match.group(1)
            # 移除前缀
            new_content = ARTICLE_PREFIX_PATTERN.sub("", content).strip()
            
            # 更新数据库
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"content": new_content}}
            )
            
            fixed_count += 1
            
            if fixed_count <= 5:
                print(f"  ✅ 修复: {article_display}")
                print(f"     原: {content[:50]}...")
                print(f"     新: {new_content[:50]}...")
                print()
        else:
            skipped_count += 1
    
    print("=" * 60)
    print(f"✅ 修复完成!")
    print(f"   已修复: {fixed_count} 条")
    print(f"   无需修复: {skipped_count} 条")
    print("=" * 60)
    
    client.close()


if __name__ == "__main__":
    try:
        fix_duplicate_prefix()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
