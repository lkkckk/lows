"""
系统设置 API - 包含首页弹窗等配置
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
