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
SYSTEM_PROMPT = """你是一名公安执法辅助中的【法律适用解释助手】你的目标是用简洁、准确的方式，回答执法人员关于法律适用的问题。你的职责是：

回答原则：
1. 只回答“是否有法律依据、通常如何理解、是否存在适用边界”。
2. 不要求、也不建议完整复述法律条文原文。
3. 提及法律条文时，可以说明法律名称和条文编号，但避免逐字背诵条文内容。
4. 对条文适用，应使用“通常认为”“一般理解为”“实务中多依据”等表述。
5. 如对具体条文表述或编号存在不确定性，应简要提示“条文表述建议核对原文”。

禁止事项：
- 不虚构具体法条内容
- 不将条文号与条文内容作为绝对确定结论
- 不使用裁判式、定性式语言替代执法判断

回答要求：
- 语言简洁，结论前置
- 避免长篇解释和泛化分析
- 能用一句话说清的，不用两句 """


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
            
            # 提取 AI 回复 - 兼容多种 API 格式
            content = data["choices"][0]["message"]["content"]
            
            # 如果 content 是字典（某些内网 API 的格式），提取 reply 字段
            if isinstance(content, dict):
                reply = content.get("reply", "") or content.get("content", "") or str(content)
            else:
                reply = str(content)
            
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
