"""
Knowledge base retrieval service for legal RAG.
"""
from typing import Any, Dict, List, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.law_service import LawService


class KnowledgeBaseService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.law_service = LawService(db)

    async def retrieve(self, query: str, top_k: int = 6) -> Dict[str, Any]:
        """
        知识库检索（支持向量搜索 + 关键词搜索）
        """
        import os
        
        # 相似度阈值
        MIN_SIMILARITY = 0.45
        
        # 优先尝试向量搜索
        vector_items = []
        vector_enabled = os.getenv("VECTOR_SEARCH_ENABLED", "true").lower() == "true"
        
        if vector_enabled:
            try:
                vector_items = await self.law_service.vector_search_for_rag(query, top_k=top_k)
                # 过滤低相似度结果
                if vector_items:
                    original_count = len(vector_items)
                    vector_items = [r for r in vector_items if r.get("similarity", 0) >= MIN_SIMILARITY]
                    if original_count > len(vector_items):
                        print(f"[KnowledgeBase] 相似度过滤: {original_count} -> {len(vector_items)} (阈值: {MIN_SIMILARITY})")
                
                if vector_items:
                    print(f"[KnowledgeBase] 向量搜索找到 {len(vector_items)} 条结果")
            except Exception as e:
                print(f"[KnowledgeBase] ⚠️ 向量搜索失败: {e}")
                vector_items = []
        
        # 关键词搜索作为补充
        keyword_items = await self.law_service.search_for_rag(query, top_k=top_k)
        print(f"[KnowledgeBase] 关键词搜索找到 {len(keyword_items)} 条结果")
        
        # 合并去重
        items = self._merge_results(vector_items, keyword_items, top_k)
        print(f"[KnowledgeBase] 合并后共 {len(items)} 条结果")
        
        context, sources = self._build_context(items, max_chars=6000, max_item_chars=1500)
        direct_answer = self._build_direct_answer(query, items)
        return {
            "items": items,
            "context": context,
            "sources": sources,
            "direct_answer": direct_answer,
        }
    
    def _merge_results(
        self,
        vector_items: List[Dict[str, Any]],
        keyword_items: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """合并向量搜索和关键词搜索结果，去重"""
        seen = set()
        merged = []
        
        # 优先使用向量搜索结果（相关性更高）
        for item in vector_items:
            key = (item.get("law_id"), item.get("article_num"), item.get("article_display"))
            if key not in seen:
                seen.add(key)
                merged.append(item)
        
        # 补充关键词搜索结果
        for item in keyword_items:
            key = (item.get("law_id"), item.get("article_num"), item.get("article_display"))
            if key not in seen:
                seen.add(key)
                merged.append(item)
        
        return merged[:top_k]

    def _build_context(
        self,
        items: List[Dict[str, Any]],
        max_chars: int,
        max_item_chars: int,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        if not items:
            return "", []

        seen = set()
        blocks = []
        sources = []
        total_chars = 0

        for item in items:
            law_id = item.get("law_id") or ""
            article_num = item.get("article_num")
            article_display = item.get("article_display") or ""
            key = (law_id, article_num, article_display)
            if key in seen:
                continue
            seen.add(key)

            law_title = item.get("law_title") or ""
            if not article_display and article_num is not None:
                article_display = f"第{article_num}条"

            content = (item.get("content") or "").strip().replace("\n", " ")
            if len(content) > max_item_chars:
                content = content[:max_item_chars].rstrip() + "..."

            block = f"《{law_title}》{article_display}：{content}"
            if total_chars + len(block) > max_chars:
                break

            blocks.append(block)
            total_chars += len(block)
            sources.append({
                "law_id": law_id,
                "law_title": law_title,
                "article_num": article_num,
                "article_display": article_display,
            })

        context = "\n".join(f"[{idx + 1}] {text}" for idx, text in enumerate(blocks))
        return context, sources

    def _build_direct_answer(self, query: str, items: List[Dict[str, Any]]) -> str:
        if not items:
            return ""

        article_num = self.law_service.parse_article_input(query)
        if not article_num:
            return ""

        law_keyword = self.law_service._extract_law_keyword(query)
        if not law_keyword:
            return ""

        matched = None
        for item in items:
            if item.get("article_num") != article_num:
                continue
            law_title = item.get("law_title") or ""
            if law_keyword and law_keyword not in law_title and law_title not in law_keyword:
                continue
            matched = item
            break

        if not matched:
            return ""

        law_title = matched.get("law_title") or ""
        article_display = matched.get("article_display") or ""
        if not article_display and article_num is not None:
            article_display = f"第{article_num}条"
        content = (matched.get("content") or "").strip()
        if not content:
            return ""

        return f"《{law_title}》{article_display}：{content}"
