"""
案件管理服务层
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import COLLECTION_CASES, COLLECTION_TRANSCRIPTS


class CaseService:
    """案件管理服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.cases = db[COLLECTION_CASES]
        self.transcripts = db[COLLECTION_TRANSCRIPTS]

    async def create_case(self, data: dict) -> dict:
        """创建案件"""
        now = datetime.utcnow()
        case_doc = {
            "case_id": str(uuid.uuid4()),
            "case_name": data["case_name"],
            "case_number": data.get("case_number", ""),
            "case_type": data["case_type"],
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "transcript_count": 0,
            "cross_analysis": None,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        await self.cases.insert_one(case_doc)
        case_doc.pop("_id", None)
        return case_doc

    async def get_case_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        case_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> dict:
        """获取案件列表（分页）"""
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        if case_type:
            query["case_type"] = case_type
        if keyword:
            import re
            safe_kw = re.escape(keyword)
            query["$or"] = [
                {"case_name": {"$regex": safe_kw, "$options": "i"}},
                {"case_number": {"$regex": safe_kw, "$options": "i"}},
                {"tags": {"$regex": safe_kw, "$options": "i"}},
            ]

        total = await self.cases.count_documents(query)
        skip = (page - 1) * page_size

        cursor = self.cases.find(query, {"_id": 0}).sort(
            [("status", 1), ("updated_at", -1)]
        ).skip(skip).limit(page_size)

        items = await cursor.to_list(length=page_size)
        total_pages = (total + page_size - 1) // page_size

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_case_detail(self, case_id: str) -> Optional[dict]:
        """获取案件详情"""
        case = await self.cases.find_one({"case_id": case_id}, {"_id": 0})
        if not case:
            return None

        # 附带笔录摘要列表
        transcripts_cursor = self.transcripts.find(
            {"case_id": case_id},
            {
                "_id": 0,
                "transcript_id": 1,
                "title": 1,
                "type": 1,
                "subject_name": 1,
                "subject_role": 1,
                "analysis_status": 1,
                "analysis.summary": 1,
                "analysis.related_laws": 1,
                "created_at": 1,
            }
        ).sort("created_at", -1)
        transcripts = await transcripts_cursor.to_list(length=100)

        # 构建笔录摘要
        transcript_summaries = []
        for t in transcripts:
            summary_item = {
                "transcript_id": t["transcript_id"],
                "title": t["title"],
                "type": t["type"],
                "subject_name": t["subject_name"],
                "subject_role": t["subject_role"],
                "analysis_status": t.get("analysis_status", "pending"),
                "created_at": t.get("created_at"),
                "summary": None,
                "related_laws_display": [],
            }
            analysis = t.get("analysis")
            if analysis:
                summary_item["summary"] = analysis.get("summary", "")
                laws = analysis.get("related_laws", [])
                summary_item["related_laws_display"] = [
                    f"《{l.get('law_title', '')}》{l.get('article_display', '')}"
                    for l in laws[:3]
                ]
            transcript_summaries.append(summary_item)

        case["transcripts"] = transcript_summaries
        return case

    async def update_case(self, case_id: str, data: dict) -> bool:
        """更新案件信息"""
        update_fields = {k: v for k, v in data.items() if v is not None}
        if not update_fields:
            return True
        update_fields["updated_at"] = datetime.utcnow()
        result = await self.cases.update_one(
            {"case_id": case_id},
            {"$set": update_fields}
        )
        return result.matched_count > 0

    async def archive_case(self, case_id: str, archive: bool = True) -> bool:
        """归档/取消归档案件"""
        new_status = "archived" if archive else "active"
        result = await self.cases.update_one(
            {"case_id": case_id},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )
        return result.matched_count > 0

    async def delete_case(self, case_id: str) -> bool:
        """删除案件（连带删除其下所有笔录）"""
        case = await self.cases.find_one({"case_id": case_id})
        if not case:
            return False
        # 删除所有关联笔录
        await self.transcripts.delete_many({"case_id": case_id})
        # 删除案件
        await self.cases.delete_one({"case_id": case_id})
        return True

    async def increment_transcript_count(self, case_id: str, delta: int = 1):
        """更新案件的笔录计数"""
        await self.cases.update_one(
            {"case_id": case_id},
            {
                "$inc": {"transcript_count": delta},
                "$set": {"updated_at": datetime.utcnow()},
            }
        )
