"""
QA 记忆服务 - 验证问答缓存/记忆库
功能：
1. 用户标记"好答案" → 存入记忆库
2. 新问题进来 → 先查记忆库中是否有相似问题
3. 命中记忆 → 直接返回验证过的答案（或注入 prompt 作为参考）
4. 管理接口 → 查看/删除记忆条目
"""
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase


# 文本相似度阈值（用于简单字符匹配判断是否为"相同问题"）
EXACT_MATCH_THRESHOLD = 0.90


def _normalize_question(q: str) -> str:
    """标准化问题文本：去掉标点、空格、统一小写"""
    import re
    q = q.strip()
    q = re.sub(r'[？?！!。，,、；;：:\s]+', '', q)
    q = q.lower()
    return q


def _question_hash(q: str) -> str:
    """对标准化后的问题生成 hash"""
    normalized = _normalize_question(q)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def _char_similarity(a: str, b: str) -> float:
    """基于字符集合的简单相似度（Jaccard-like）"""
    if not a or not b:
        return 0.0
    na = _normalize_question(a)
    nb = _normalize_question(b)
    if na == nb:
        return 1.0
    # 使用 2-gram 计算相似度
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1)) if len(s) > 1 else {s}
    sa = bigrams(na)
    sb = bigrams(nb)
    if not sa or not sb:
        return 0.0
    intersection = sa & sb
    union = sa | sb
    return len(intersection) / len(union) if union else 0.0


class QAMemoryService:
    """QA 记忆库服务"""

    COLLECTION_NAME = "qa_memory"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]

    async def ensure_indexes(self):
        """确保索引存在"""
        await self.collection.create_index("question_hash", unique=True)
        await self.collection.create_index("created_at")
        await self.collection.create_index("use_count")

    # ==================== 核心功能 ====================

    async def find_match(self, question: str) -> Optional[Dict[str, Any]]:
        """
        查找记忆库中是否有匹配的已验证问答。
        策略：
        1. 精确 hash 匹配（完全相同的问题）
        2. 遍历记忆库计算字符相似度（应对微小措辞差异）
        
        返回匹配的记忆条目，或 None
        """
        if not question or not question.strip():
            return None

        # 第一步：精确 hash 匹配
        qhash = _question_hash(question)
        exact = await self.collection.find_one({"question_hash": qhash})
        if exact:
            # 更新使用次数
            await self.collection.update_one(
                {"_id": exact["_id"]},
                {"$inc": {"use_count": 1}, "$set": {"last_used_at": datetime.utcnow()}}
            )
            exact["_id"] = str(exact["_id"])
            exact["match_type"] = "exact"
            return exact

        # 第二步：字符相似度匹配（只对记忆库较小时可行）
        # 限制扫描量，避免性能问题
        cursor = self.collection.find(
            {},
            {"question": 1, "answer": 1, "sources": 1, "question_hash": 1, "use_count": 1}
        ).sort("use_count", -1).limit(200)
        
        memories = await cursor.to_list(length=200)
        
        best_match = None
        best_score = 0.0
        
        for mem in memories:
            score = _char_similarity(question, mem.get("question", ""))
            if score > best_score:
                best_score = score
                best_match = mem
        
        if best_match and best_score >= EXACT_MATCH_THRESHOLD:
            # 更新使用次数
            await self.collection.update_one(
                {"_id": best_match["_id"]},
                {"$inc": {"use_count": 1}, "$set": {"last_used_at": datetime.utcnow()}}
            )
            best_match["_id"] = str(best_match["_id"])
            best_match["match_type"] = "similar"
            best_match["similarity"] = best_score
            return best_match

        return None

    async def find_related(self, question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        查找相关但不完全匹配的记忆条目（用作 few-shot 参考）
        阈值低于 EXACT_MATCH_THRESHOLD，但有一定相关性
        """
        if not question or not question.strip():
            return []

        cursor = self.collection.find(
            {},
            {"question": 1, "answer": 1, "sources": 1, "use_count": 1}
        ).sort("use_count", -1).limit(200)
        
        memories = await cursor.to_list(length=200)
        
        scored = []
        for mem in memories:
            score = _char_similarity(question, mem.get("question", ""))
            if score >= 0.3 and score < EXACT_MATCH_THRESHOLD:
                mem["_id"] = str(mem["_id"])
                mem["similarity"] = score
                scored.append(mem)
        
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    # ==================== 反馈写入 ====================

    async def save_good_answer(
        self,
        question: str,
        answer: str,
        sources: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """
        保存一个"好答案"到记忆库
        如果问题已存在，会更新答案
        """
        qhash = _question_hash(question)
        
        doc = {
            "question_hash": qhash,
            "question": question.strip(),
            "answer": answer.strip(),
            "sources": sources or [],
            "created_at": datetime.utcnow(),
            "last_used_at": datetime.utcnow(),
            "use_count": 0,
        }
        
        result = await self.collection.update_one(
            {"question_hash": qhash},
            {"$set": doc},
            upsert=True,
        )
        
        action = "updated" if result.matched_count > 0 else "created"
        return {"success": True, "action": action, "question_hash": qhash}

    async def mark_bad_answer(self, question: str) -> Dict[str, Any]:
        """
        标记某个问题的答案为"坏答案" → 从记忆库中删除（如果存在）
        这样下次会重新走 LLM
        """
        qhash = _question_hash(question)
        result = await self.collection.delete_one({"question_hash": qhash})
        return {
            "success": True,
            "deleted": result.deleted_count > 0,
        }

    # ==================== 管理接口 ====================

    async def list_memories(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """分页列出记忆库内容"""
        import math
        total = await self.collection.count_documents({})
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        skip = (page - 1) * page_size

        cursor = self.collection.find({}).sort("use_count", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        
        for item in items:
            item["_id"] = str(item["_id"])
        
        return {
            "data": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        }

    async def delete_memory(self, question_hash: str) -> bool:
        """删除单条记忆"""
        result = await self.collection.delete_one({"question_hash": question_hash})
        return result.deleted_count > 0

    async def clear_all(self) -> int:
        """清空所有记忆"""
        result = await self.collection.delete_many({})
        return result.deleted_count

    async def get_stats(self) -> Dict[str, Any]:
        """获取记忆库统计"""
        total = await self.collection.count_documents({})
        total_used = await self.collection.count_documents({"use_count": {"$gt": 0}})
        
        # 总使用次数
        pipeline = [{"$group": {"_id": None, "total_hits": {"$sum": "$use_count"}}}]
        agg = await self.collection.aggregate(pipeline).to_list(length=1)
        total_hits = agg[0]["total_hits"] if agg else 0
        
        return {
            "total_entries": total,
            "entries_used": total_used,
            "total_hits": total_hits,
        }
