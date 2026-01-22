"""
系统设置 API - 包含首页弹窗、AI模型配置等
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
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
        }
    # 返回默认配置
    return {
        "provider": "deepseek",
        "api_url": AI_PRESETS["deepseek"]["api_url"],
        "api_key": "",
        "model_name": AI_PRESETS["deepseek"]["model_name"],
        "skip_ssl_verify": False,
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
            }
        },
        upsert=True,
    )
    return {"success": True, "message": "AI 配置已保存"}

