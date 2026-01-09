"""
API 路由包初始化
"""
from fastapi import APIRouter
from .laws import router as laws_router
from .templates import router as templates_router
from .settings import router as settings_router
from .auth import router as auth_router
from .ai import router as ai_router

api_router = APIRouter()

# 注册子路由
api_router.include_router(laws_router)
api_router.include_router(templates_router)
api_router.include_router(settings_router)
api_router.include_router(auth_router)
api_router.include_router(ai_router)

__all__ = ["api_router"]

