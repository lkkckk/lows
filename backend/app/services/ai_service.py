"""
AI 服务模块 - 从数据库读取配置，支持动态切换模型
"""
import os
import httpx
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.knowledge_base_service import KnowledgeBaseService

# 默认配置（当数据库无配置时使用）
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 系统提示词 - 定义 AI 助手人设（RAG 优化版）
SYSTEM_PROMPT = """你是一名公安执法辅助中的【法律适用解释助手】，目标是用简洁、准确的方式回答执法人员关于法律适用的问题。

回答原则：
1. 优先引用系统检索到的法规条文（已在上下文中提供），并给出完整的法名与条号。
2. 对条文适用可使用"通常认为""一般理解为""实务中多依据"等表述。
3. 如检索结果未覆盖问题，应明确告知"未检索到相关条文，建议核对原文"。

禁止事项：
- 不得虚构未在上下文中出现的法条内容
- 不使用裁判式、定性式语言替代执法判断

回答要求：
- 语言简洁，结论前置
- 能用一句话说清的，不用两句"""


async def get_ai_config(db: AsyncIOMotorDatabase) -> dict:
    """从数据库获取 AI 配置"""
    settings = await db.settings.find_one({"key": "ai_config"})
    if settings:
        return {
            "api_url": settings.get("api_url", DEFAULT_API_URL),
            "api_key": settings.get("api_key", DEFAULT_API_KEY),
            "model_name": settings.get("model_name", DEFAULT_MODEL),
            "skip_ssl_verify": settings.get("skip_ssl_verify", False),
            "provider": settings.get("provider", "default"),
            "rag_enabled": settings.get("rag_enabled", True),
            "rag_top_k": settings.get("rag_top_k", 6),
        }
    # 返回默认配置
    return {
        "api_url": DEFAULT_API_URL,
        "api_key": DEFAULT_API_KEY,
        "model_name": DEFAULT_MODEL,
        "skip_ssl_verify": False,
        "provider": "default",
        "rag_enabled": True,
        "rag_top_k": 6,
    }


def _build_messages(message: str, history: Optional[list], context: str) -> List[Dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({
            "role": "system",
            "content": "以下为可引用的法规条文摘要：\n"
            + context
            + "\n回答时应优先引用上述条文，并给出法名与条号。若未检索到明确依据，请说明需核对原文。",
        })
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    return messages


def _extract_reply(data: Dict[str, Any]) -> str:
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, dict):
        return content.get("reply", "") or content.get("content", "") or str(content)
    return str(content)


async def chat_with_ai(
    message: str,
    history: Optional[list] = None,
    db: AsyncIOMotorDatabase = None,
    use_rag: bool = True,
    rag_top_k: Optional[int] = None,
) -> Dict[str, Any]:
    """
    与 AI 进行对话（从数据库读取配置）
    
    Args:
        message: 用户消息
        history: 对话历史（可选）
        db: 数据库连接
    
    Returns:
        包含 reply 和 usage 的字典
    """
    # 获取配置
    if db is not None:
        config = await get_ai_config(db)
    else:
        config = {
            "api_url": DEFAULT_API_URL,
            "api_key": DEFAULT_API_KEY,
            "model_name": DEFAULT_MODEL,
            "skip_ssl_verify": False,
        }
    
    rag_enabled = config.get("rag_enabled", True)
    top_k = rag_top_k if rag_top_k is not None else config.get("rag_top_k", 6)
    rag_context = ""
    rag_sources = []
    direct_answer = ""

    if db is not None and use_rag and rag_enabled:
        kb_service = KnowledgeBaseService(db)
        rag_data = await kb_service.retrieve(message, top_k=top_k)
        rag_context = rag_data.get("context", "")
        rag_sources = rag_data.get("sources", [])
        direct_answer = rag_data.get("direct_answer", "")

    if use_rag and rag_enabled and direct_answer:
        return {
            "reply": direct_answer,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "provider": "knowledge_base",
            "sources": rag_sources,
        }

    if use_rag and rag_enabled and not rag_context:
        return {
            "reply": "未检索到明确的法规条文，请核对法规名称或更新知识库。",
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "provider": "knowledge_base",
            "sources": [],
        }

    messages = _build_messages(message, history, rag_context)

    api_url = config.get("api_url", DEFAULT_API_URL)
    if not api_url:
        raise Exception("AI 服务未配置 API URL，请在后台管理页面配置")
    api_key = config.get("api_key", DEFAULT_API_KEY) or ""
    model = config.get("model_name", DEFAULT_MODEL)
    skip_ssl_verify = config.get("skip_ssl_verify", False)
    timeout = 60.0
    provider_id = config.get("provider", "default")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=not skip_ssl_verify) as client:
            response = await client.post(
                api_url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

        reply = _extract_reply(data)
        usage = data.get("usage", {})
        return {
            "reply": reply,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "provider": provider_id,
            "sources": rag_sources,
        }
    except httpx.HTTPStatusError as e:
        error_msg = f"AI 服务请求失败: {e.response.status_code}"
        if e.response.status_code == 401:
            error_msg = "AI 服务认证失败，请检查 API Key 配置"
        elif e.response.status_code == 429:
            error_msg = "AI 服务请求频率过高，请稍后重试"
        raise Exception(error_msg)
    except httpx.TimeoutException:
        raise Exception("AI 服务响应超时，请稍后重试")
    except Exception as e:
        raise Exception(f"AI 服务出错: {str(e)}")
