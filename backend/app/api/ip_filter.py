"""
IP 访问控制模块 - 基于 IP 白名单的访问过滤
"""
import ipaddress
from typing import List, Optional
from fastapi import Request, HTTPException
from app.db import get_database


async def get_ip_access_config() -> dict:
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


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    # 优先从 X-Forwarded-For 获取（经过代理时）
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个 IP（最原始的客户端 IP）
        return forwarded.split(",")[0].strip()
    
    # 其次从 X-Real-IP 获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 最后使用直连 IP
    return request.client.host if request.client else "unknown"


def is_ip_in_whitelist(client_ip: str, whitelist: List[str]) -> bool:
    """检查 IP 是否在白名单中（支持 CIDR 格式）"""
    if not whitelist:
        return False  # 空白名单表示不允许访问
    
    try:
        client = ipaddress.ip_address(client_ip)
        for entry in whitelist:
            entry = entry.strip()
            if not entry:
                continue
            try:
                # 尝试解析为网络（CIDR 格式）
                if "/" in entry:
                    network = ipaddress.ip_network(entry, strict=False)
                    if client in network:
                        return True
                else:
                    # 单个 IP 地址
                    if client == ipaddress.ip_address(entry):
                        return True
            except ValueError:
                continue  # 跳过无效条目
        return False
    except ValueError:
        return False  # 无效的客户端 IP


async def verify_ai_access(request: Request):
    """验证 AI 功能访问权限"""
    config = await get_ip_access_config()
    
    # 如果未启用过滤，直接放行
    if not config["ai_enabled"]:
        return True
    
    client_ip = get_client_ip(request)
    
    if not is_ip_in_whitelist(client_ip, config["ai_whitelist"]):
        raise HTTPException(
            status_code=403,
            detail=f"您的 IP ({client_ip}) 无权访问 AI 功能，请联系管理员"
        )
    
    return True


async def verify_internal_docs_access(request: Request):
    """验证内部规章访问权限"""
    config = await get_ip_access_config()
    
    # 如果未启用过滤，直接放行
    if not config["internal_docs_enabled"]:
        return True
    
    client_ip = get_client_ip(request)
    
    if not is_ip_in_whitelist(client_ip, config["internal_docs_whitelist"]):
        raise HTTPException(
            status_code=403,
            detail=f"您的 IP ({client_ip}) 无权访问内部规章，请联系管理员"
        )
    
    return True
