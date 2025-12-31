"""
简易鉴权 API - 仅用于极简管理密码校验
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
import os

router = APIRouter(prefix="/auth", tags=["鉴权"])

# 默认管理员密码
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
async def login(data: LoginRequest):
    """验证管理员密码"""
    if data.password == ADMIN_PASSWORD:
        return {"success": True, "token": ADMIN_PASSWORD, "message": "登录成功"}
    raise HTTPException(status_code=401, detail="密码错误")

async def verify_admin(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """管理接口校验依赖"""
    if x_admin_token != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="未授权访问或登录已过期")
    return True
