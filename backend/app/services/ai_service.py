"""
AI 服务模块 - 从数据库读取配置，支持动态切换模型
"""
import os
import httpx
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

# 默认配置（当数据库无配置时使用）
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 系统提示词 - 定义 AI 助手人设
SYSTEM_PROMPT = """你是一位专业的法律助手，服务于中国公安执法人员。你的职责是：
1. 解答法律相关问题，特别是刑法、刑事诉讼法、治安管理处罚法等公安常用法律
2. 提供准确、专业的法律解释和法条引用
3. 语言简洁明了，适合执法实务参考
4. 如果问题超出法律范围，礼貌地引导用户回到法律话题
5. 对于复杂或敏感问题，建议用户咨询专业律师或法务部门

注意：你的回答仅供参考，不构成正式法律意见。"""


async def get_ai_config(db: AsyncIOMotorDatabase) -> dict:
    """从数据库获取 AI 配置"""
    settings = await db.settings.find_one({"key": "ai_config"})
    if settings:
        return {
            "api_url": settings.get("api_url", DEFAULT_API_URL),
            "api_key": settings.get("api_key", DEFAULT_API_KEY),
            "model_name": settings.get("model_name", DEFAULT_MODEL),
            "skip_ssl_verify": settings.get("skip_ssl_verify", False),
        }
    # 返回默认配置
    return {
        "api_url": DEFAULT_API_URL,
        "api_key": DEFAULT_API_KEY,
        "model_name": DEFAULT_MODEL,
        "skip_ssl_verify": False,
    }


async def chat_with_ai(message: str, history: Optional[list] = None, db: AsyncIOMotorDatabase = None) -> Dict[str, Any]:
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
    
    api_url = config["api_url"]
    api_key = config["api_key"]
    model_name = config["model_name"]
    skip_ssl_verify = config["skip_ssl_verify"]
    
    if not api_key:
        raise Exception("AI 服务未配置 API Key，请在后台管理页面配置")
    
    # 构建消息列表
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 添加历史对话（如果有）
    if history:
        messages.extend(history)
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": message})
    
    # 调用 AI API
    async with httpx.AsyncClient(timeout=60.0, verify=not skip_ssl_verify) as client:
        try:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # 提取 AI 回复
            reply = data["choices"][0]["message"]["content"]
            
            # 提取 Token 统计（如果 API 返回）
            usage = data.get("usage", {})
            
            return {
                "reply": reply,
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
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
