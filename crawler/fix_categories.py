import os
import re
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env'))

def fix_categories():
    # 连接 MongoDB
    mongo_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27019")
    db_name = os.getenv("MONGODB_DB", "law_system")
    
    logging.info(f"🔗 连接 MongoDB: {mongo_uri}, 数据库: {db_name}")
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    # 获取分类统计
    all_categories = list(db.laws.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]))
    logging.info(f"📊 当前分类统计: {all_categories}")
    
    # 获取所有分类为空或未定义的法规
    laws_to_fix = list(db.laws.find({
        "$or": [
            {"category": {"$in": ["", None, "未分类"]}},
            {"category": {"$exists": False}}
        ]
    }))
    
    if not laws_to_fix:
        logging.info("✅ 没有需要修复分类的法规。")
        return

    logging.info(f"🔍 发现 {len(laws_to_fix)} 部法规分类缺失，开始修复...")
    
    fixed_count = 0
    for law in laws_to_fix:
        title = law.get("title", "")
        law_id = law.get("law_id")
        
        # 智能分类逻辑（同步自 import_local.py）
        new_category = ""
        if "解释" in title or "关于" in title:
            new_category = "司法解释"
        elif "刑" in title or "罪" in title:
            new_category = "刑事法律"
        elif "治安" in title or "行政" in title:
            new_category = "行政法律"
        elif ("程" in title and "定" in title) or "诉讼" in title:
            new_category = "程序规定"
        elif "办法" in title or "规定" in title or "条例" in title:
            new_category = "行政法律" # 默认归类为行政法律或部门规章
        else:
            new_category = "行政法律" # 默认兜底
            
        if new_category:
            db.laws.update_one(
                {"law_id": law_id},
                {"$set": {"category": new_category}}
            )
            fixed_count += 1
            logging.info(f"   ✅ 已修复: [{new_category}] {title}")

    logging.info(f"🎉 修复完成！共修复 {fixed_count} 条数据。")

if __name__ == "__main__":
    fix_categories()
