"""
AI 问法 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List

from app.services.ai_service import chat_with_ai
from app.services.qa_memory_service import QAMemoryService
from app.db import get_database
from .ip_filter import verify_ai_access

router = APIRouter(prefix="/ai", tags=["AI 问法"])


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" 或 "assistant"
    content: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    history: Optional[List[ChatMessage]] = None
    use_rag: bool = True
    rag_top_k: Optional[int] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    reply: str
    success: bool = True
    provider: Optional[str] = None
    sources: Optional[List[dict]] = None
    from_memory: bool = False


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    question: str
    answer: str
    is_good: bool  # True=好答案, False=坏答案
    sources: Optional[List[dict]] = None


async def record_token_usage(db, usage: dict):
    """记录 Token 使用量到数据库"""
    if not usage or usage.get("total_tokens", 0) == 0:
        return
    
    await db.settings.update_one(
        {"key": "ai_token_usage"},
        {
            "$inc": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "call_count": 1,
            }
        },
        upsert=True,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest, _ip_check: bool = Depends(verify_ai_access)):
    """
    与 AI 法律助手对话
    
    - **message**: 用户问题
    - **history**: 对话历史（可选）
    """
    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    try:
        # 转换历史记录格式
        history = None
        if chat_request.history:
            history = [{"role": msg.role, "content": msg.content} for msg in chat_request.history]
        
        # 获取数据库连接
        db = get_database()
        
        # 调用 AI 服务（传递数据库以读取配置）
        result = await chat_with_ai(
            chat_request.message,
            history,
            db,
            use_rag=chat_request.use_rag,
            rag_top_k=chat_request.rag_top_k,
        )
        
        # 记录 Token 使用量
        await record_token_usage(db, result.get("usage", {}))
        
        return ChatResponse(
            reply=result["reply"],
            success=True,
            provider=result.get("provider"),
            sources=result.get("sources"),
            from_memory=result.get("from_memory", False),
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(request: Request, feedback: FeedbackRequest):
    """
    提交答案反馈（好/坏）
    
    - 好答案：存入记忆库，下次相同问题直接返回
    - 坏答案：从记忆库删除（如果存在），下次重新走 LLM
    """
    try:
        db = get_database()
        memory_service = QAMemoryService(db)
        
        if feedback.is_good:
            result = await memory_service.save_good_answer(
                question=feedback.question,
                answer=feedback.answer,
                sources=feedback.sources,
            )
            return {"success": True, "message": "已记住此回答", "action": result.get("action")}
        else:
            result = await memory_service.mark_bad_answer(question=feedback.question)
            return {"success": True, "message": "已标记为不满意", "deleted": result.get("deleted")}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats")
async def get_memory_stats(request: Request):
    """获取记忆库统计信息"""
    try:
        db = get_database()
        memory_service = QAMemoryService(db)
        stats = await memory_service.get_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/list")
async def list_memories(request: Request, page: int = 1, page_size: int = 20):
    """分页列出记忆库内容"""
    try:
        db = get_database()
        memory_service = QAMemoryService(db)
        result = await memory_service.list_memories(page, page_size)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/{question_hash}")
async def delete_memory(request: Request, question_hash: str):
    """删除单条记忆"""
    try:
        db = get_database()
        memory_service = QAMemoryService(db)
        deleted = await memory_service.delete_memory(question_hash)
        if not deleted:
            raise HTTPException(status_code=404, detail="记忆条目不存在")
        return {"success": True, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

