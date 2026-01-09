"""
AI 服务模块 - 封装 DeepSeek API 调用
"""
import os
import httpx
from typing import Optional

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-5c3527fd88614f818d18c45a93dcf5da")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 系统提示词 - 定义 AI 助手人设
SYSTEM_PROMPT = """你是一位专业的法律助手，服务于中国公安执法人员。你的职责是：
1. 解答法律相关问题，特别是刑法、刑事诉讼法、治安管理处罚法等公安常用法律
2. 提供准确、专业的法律解释和法条引用
3. 语言简洁明了，适合执法实务参考
4. 如果问题超出法律范围，礼貌地引导用户回到法律话题
5. 对于复杂或敏感问题，建议用户咨询专业律师或法务部门

注意：你的回答仅供参考，不构成正式法律意见。"""


async def chat_with_ai(message: str, history: Optional[list] = None) -> str:
    """
    与 DeepSeek AI 进行对话
    
    Args:
        message: 用户消息
        history: 对话历史（可选）
    
    Returns:
        AI 回复内容
    """
    # 构建消息列表
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 添加历史对话（如果有）
    if history:
        messages.extend(history)
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": message})
    
    # 调用 DeepSeek API
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # 提取 AI 回复
            return data["choices"][0]["message"]["content"]
            
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
