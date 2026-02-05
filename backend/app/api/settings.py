"""
系统设置 API - 包含首页弹窗、AI模型配置等
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from app.db import get_database
from .auth import verify_admin

router = APIRouter(prefix="/settings", tags=["系统设置"])


class PopupSettings(BaseModel):
    """首页弹窗配置"""
    enabled: bool = False
    title: str = ""
    content: str = ""


class AISettings(BaseModel):
    """AI 模型配置"""
    provider: str = "deepseek"  # deepseek, ruizhi, custom
    api_url: str = "https://api.deepseek.com/v1/chat/completions"
    api_key: str = ""
    model_name: str = "deepseek-chat"
    skip_ssl_verify: bool = False
    rag_enabled: bool = True
    rag_top_k: int = 6
    use_function_calling: bool = True  # 是否使用 Function Calling


# 预设模型配置
AI_PRESETS = {
    "deepseek": {
        "name": "DeepSeek (云端)",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model_name": "deepseek-chat",
        "skip_ssl_verify": False,
    },
    "ruizhi": {
        "name": "锐智AI (内网)",
        "api_url": "https://10.2.164.106/v2/chat/completions",
        "model_name": "ayenaspring-pro-001",
        "skip_ssl_verify": True,
    },
    "qwen": {
        "name": "Qwen (内网)",
        "api_url": "http://127.0.0.1:8000/v1/chat/completions",
        "model_name": "qwen2.5",
        "skip_ssl_verify": True,
    },
}


@router.get("/popup", response_model=PopupSettings)
async def get_popup_settings():
    """获取首页弹窗设置"""
    db = get_database()
    settings = await db.settings.find_one({"key": "homepage_popup"})
    if settings:
        return PopupSettings(
            enabled=settings.get("enabled", False),
            title=settings.get("title", ""),
            content=settings.get("content", ""),
        )
    return PopupSettings()


@router.put("/popup")
async def update_popup_settings(data: PopupSettings, _admin: bool = Depends(verify_admin)):
    """更新首页弹窗设置"""
    db = get_database()
    await db.settings.update_one(
        {"key": "homepage_popup"},
        {
            "$set": {
                "enabled": data.enabled,
                "title": data.title,
                "content": data.content,
            }
        },
        upsert=True,
    )
    return {"success": True, "message": "弹窗设置已保存"}


@router.get("/ai")
async def get_ai_settings():
    """获取 AI 模型配置"""
    db = get_database()
    settings = await db.settings.find_one({"key": "ai_config"})
    if settings:
        return {
            "provider": settings.get("provider", "deepseek"),
            "api_url": settings.get("api_url", ""),
            "api_key": settings.get("api_key", ""),
            "model_name": settings.get("model_name", ""),
            "skip_ssl_verify": settings.get("skip_ssl_verify", False),
            "rag_enabled": settings.get("rag_enabled", True),
            "rag_top_k": settings.get("rag_top_k", 6),
            "use_function_calling": settings.get("use_function_calling", True),
        }
    # 返回默认配置
    return {
        "provider": "deepseek",
        "api_url": AI_PRESETS["deepseek"]["api_url"],
        "api_key": "",
        "model_name": AI_PRESETS["deepseek"]["model_name"],
        "skip_ssl_verify": False,
        "rag_enabled": True,
        "rag_top_k": 6,
        "use_function_calling": True,
    }


@router.get("/ai/presets")
async def get_ai_presets():
    """获取预设模型列表"""
    return AI_PRESETS


@router.put("/ai")
async def update_ai_settings(data: AISettings, _admin: bool = Depends(verify_admin)):
    """更新 AI 模型配置"""
    db = get_database()
    await db.settings.update_one(
        {"key": "ai_config"},
        {
            "$set": {
                "provider": data.provider,
                "api_url": data.api_url,
                "api_key": data.api_key,
                "model_name": data.model_name,
                "skip_ssl_verify": data.skip_ssl_verify,
                "rag_enabled": data.rag_enabled,
                "rag_top_k": data.rag_top_k,
                "use_function_calling": data.use_function_calling,
            }
        },
        upsert=True,
    )
    return {"success": True, "message": "AI 配置已保存"}


# ==================== AI Token 用量统计 ====================

@router.get("/ai/token-usage")
async def get_ai_token_usage():
    """获取 AI Token 累计使用量"""
    db = get_database()
    settings = await db.settings.find_one({"key": "ai_token_usage"})
    if settings:
        return {
            "prompt_tokens": settings.get("prompt_tokens", 0),
            "completion_tokens": settings.get("completion_tokens", 0),
            "total_tokens": settings.get("total_tokens", 0),
            "call_count": settings.get("call_count", 0),
        }
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "call_count": 0,
    }


# ==================== IP 访问控制配置 ====================

class IPAccessSettings(BaseModel):
    """IP 访问控制配置"""
    ai_enabled: bool = False
    ai_whitelist: List[str] = Field(default_factory=list)
    internal_docs_enabled: bool = False
    internal_docs_whitelist: List[str] = Field(default_factory=list)


@router.get("/ip-access")
async def get_ip_access_settings():
    """获取 IP 访问控制配置"""
    db = get_database()
    settings = await db.settings.find_one({"key": "ip_access_config"})
    if settings:
        return {
            "ai_enabled": settings.get("ai_enabled", False),
            "ai_whitelist": settings.get("ai_whitelist", []),
            "internal_docs_enabled": settings.get("internal_docs_enabled", False),
            "internal_docs_whitelist": settings.get("internal_docs_whitelist", []),
        }
    return {
        "ai_enabled": False,
        "ai_whitelist": [],
        "internal_docs_enabled": False,
        "internal_docs_whitelist": [],
    }


@router.put("/ip-access")
async def update_ip_access_settings(data: IPAccessSettings, _admin: bool = Depends(verify_admin)):
    """更新 IP 访问控制配置"""
    ai_whitelist = [
        item.strip()
        for item in data.ai_whitelist
        if isinstance(item, str) and item.strip()
    ]
    internal_docs_whitelist = [
        item.strip()
        for item in data.internal_docs_whitelist
        if isinstance(item, str) and item.strip()
    ]
    if data.ai_enabled and not ai_whitelist:
        raise HTTPException(status_code=400, detail="开启 AI 访问控制时必须配置 IP 白名单")
    if data.internal_docs_enabled and not internal_docs_whitelist:
        raise HTTPException(status_code=400, detail="开启内部规章访问控制时必须配置 IP 白名单")
    db = get_database()
    await db.settings.update_one(
        {"key": "ip_access_config"},
        {
            "$set": {
                "ai_enabled": data.ai_enabled,
                "ai_whitelist": ai_whitelist,
                "internal_docs_enabled": data.internal_docs_enabled,
                "internal_docs_whitelist": internal_docs_whitelist,
            }
        },
        upsert=True,
    )
    return {"success": True, "message": "IP 访问控制配置已保存"}

