"""
AI 问法 API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.services.ai_service import chat_with_ai
from app.db import get_database

router = APIRouter(prefix="/ai", tags=["AI 问法"])


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" 或 "assistant"
    content: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    reply: str
    success: bool = True


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    与 AI 法律助手对话
    
    - **message**: 用户问题
    - **history**: 对话历史（可选）
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    try:
        # 转换历史记录格式
        history = None
        if request.history:
            history = [{"role": msg.role, "content": msg.content} for msg in request.history]
        
        # 获取数据库连接
        db = get_database()
        
        # 调用 AI 服务（传递数据库以读取配置）
        reply = await chat_with_ai(request.message, history, db)
        
        return ChatResponse(reply=reply, success=True)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

