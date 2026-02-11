"""
AI 服务模块 - 支持 Function Calling 让 AI 自主查询知识库
"""
import json
import os
import httpx
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.law_service import LawService

# 默认配置（当数据库无配置时使用）
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 系统提示词 - 定义 AI 助手人设（Function Calling 版本）
SYSTEM_PROMPT = """你是一名公安执法辅助中的【法律适用解释助手】，目标是用简洁、准确的方式回答执法人员关于法律适用的问题。

你可以使用 search_legal_knowledge 工具来检索法规知识库，获取相关法律条文。

【重要】关于法律版本：
- 系统已自动过滤旧版本法规，检索结果中的条文均为最新版本
- 直接引用检索结果中的法名、条号和内容，不要自行推断或修改条号
- 如检索结果中显示"2025年修订"等版本信息，请在回答中明确标注

【关键】法律名称规范化：
- 法律名称可能带版本后缀，如"（2018年修正）"、"（2025年修订）"等
- 在验证用户引用时，应忽略版本后缀进行比较
- 例如："《中华人民共和国刑事诉讼法》"与"《中华人民共和国刑事诉讼法（2018年修正）》"是同一部法律
- 只要核心法律名称相同、条号相同、内容一致，就应判定为"正确"

【核心】条文引用验证 vs 法律适用分析：
当用户询问"引用的条文是否正确"或类似问题时，你需要区分两个层面：
1. 【形式验证】：法律名称、条号、内容是否与数据库一致？——这是主要回答内容
2. 【适用建议】：该条文是否最适合用户的具体场景？——仅作为参考意见，不作为"是否正确"的判断依据

判定原则：
- 只要法名、条号正确，且条文内容确实来自该法律，就应判定为"引用正确"
- 至于该条文是否是"最佳选择"，可以作为补充建议，但不能因此判定"引用错误"
- 例如：用户引用《刑事诉讼法》第144条查询银行卡交易明细，该条确实授权查询财产（存款、汇款等），交易明细属于财产信息的体现，引用是正确的

回答原则：
1. 对于涉及法律法规的问题，应先调用工具检索相关条文，再基于检索结果回答。
2. 严格按照检索结果引用法条，完整给出法名、版本、条号。
3. 不要混用不同版本的法条信息（如条号和处罚金额必须来自同一版本）。
4. 对条文适用可使用"通常认为""一般理解为""实务中多依据"等表述。

禁止事项：
- 不得虚构未经检索确认的法条内容
- 不得自行推测条号（必须使用检索结果中的条号）
- 不使用裁判式、定性式语言替代执法判断
- 不要因"可能有更合适的条文"而否定用户正确引用的条文

回答要求：
- 语言简洁，结论前置
- 能用一句话说清的，不用两句"""

# Function Calling 工具定义
LEGAL_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_legal_knowledge",
        "description": "搜索法规知识库，根据关键词或法条信息检索相关法律条文。对于任何涉及法律法规的问题，都应该调用此工具获取准确信息。系统会自动返回最新版本的法规，无需在关键词中指定年份或版本。",
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "搜索关键词。【重要】只提取核心行为词或法律名称，不要加'处罚''如何''怎么'等后缀。正确示例：'赌博'（而非'赌博处罚'）、'卖淫'（而非'卖淫如何处罚'）、'醉驾'、'治安管理处罚法'"
                },
                "law_name": {
                    "type": "string",
                    "description": "具体法律名称（可选），如'刑法'、'治安管理处罚法'、'道路交通安全法'。不要包含年份或版本后缀。"
                },
                "article_num": {
                    "type": "integer",
                    "description": "具体条号（可选），如18、112、273"
                }
            },
            "required": ["keywords"]
        }
    }
}


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
            "use_function_calling": settings.get("use_function_calling", True),
        }
    return {
        "api_url": DEFAULT_API_URL,
        "api_key": DEFAULT_API_KEY,
        "model_name": DEFAULT_MODEL,
        "skip_ssl_verify": False,
        "provider": "default",
        "rag_enabled": True,
        "rag_top_k": 6,
        "use_function_calling": True,
    }


def _looks_like_law_name(name: str) -> bool:
    """判断是否像法律名称"""
    law_indicators = ["法", "条例", "规定", "规则", "办法", "解释", "意见", "通知", "决定"]
    return any(ind in name for ind in law_indicators)


def _get_law_year(title: str) -> int:
    """从法律标题中提取年份"""
    import re
    year_pattern = r'[（\(](\d{4})年[修订正]+[）\)]'
    match = re.search(year_pattern, title)
    return int(match.group(1)) if match else 0


def _get_law_base_name(title: str) -> str:
    """提取法律基础名称（去掉年份部分）"""
    import re
    year_pattern = r'[（\(]\d{4}年[修订正]+[）\)]'
    return re.sub(year_pattern, '', title).strip()


async def execute_search_legal_knowledge(
    db: AsyncIOMotorDatabase,
    keywords: str,
    law_name: Optional[str] = None,
    article_num: Optional[int] = None,
    top_k: int = 6,
) -> Dict[str, Any]:
    """
    执行法规知识库检索（Function Calling 工具实现）
    
    检索策略：
    1. 如果有明确条号（article_num），走精准条号查找
    2. 始终尝试向量搜索作为主要检索方式
    3. 如果有 law_name 且标题匹配成功，用匹配到的 law_ids 过滤向量搜索结果
    4. 关键词正则搜索作为兜底补充
    5. 将向量搜索结果和关键词搜索结果去重合并
    """
    import re
    import os
    
    law_service = LawService(db)
    laws_collection = db["laws"]
    articles_collection = db["law_articles"]
    
    # 相似度阈值
    MIN_SIMILARITY = 0.45
    
    # ========== 关键词清理 ==========
    # 去除常见的查询后缀词，提取核心行为词
    suffix_pattern = r'(处罚|规定|条款|法律|法规|如何|怎么|什么|相关|行为)$'
    clean_keywords = re.sub(suffix_pattern, '', keywords).strip() if keywords else keywords
    if clean_keywords and clean_keywords != keywords:
        print(f"[AI Service] 关键词清理: '{keywords}' -> '{clean_keywords}'")
        keywords = clean_keywords
    
    # ========== 同义词扩展 ==========
    # 口语化表达 → 法律用语
    SYNONYM_MAP = {
        "醉驾": "醉酒",
        "酒驾": "饮酒",
        "打架": "殴打",
        "偷东西": "盗窃",
        "骗钱": "诈骗",
        "抢钱": "抢劫",
        "嫖": "嫖娼",
        "黄赌毒": "赌博",
        "吸粉": "吸毒",
        "贩粉": "贩毒",
        "打人": "殴打",
    }
    if keywords in SYNONYM_MAP:
        original = keywords
        keywords = SYNONYM_MAP[keywords]
        print(f"[AI Service] 同义词映射: '{original}' -> '{keywords}'")
    
    print(f"[AI Service] 检索参数 - keywords: '{keywords}', law_name: '{law_name}', article_num: {article_num}")
    
    # ========== 步骤 1: 精准条号查找 ==========
    if article_num:
        print(f"[AI Service] 精准条号查找: 第{article_num}条")
        
        # 构建查询条件
        article_query = {}
        if law_name:
            # 如果指定了法律名称，先匹配法律
            if _looks_like_law_name(law_name):
                law_name_pattern = law_name.replace("中华人民共和国", "").strip()
                law_regex = {"title": {"$regex": law_name_pattern, "$options": "i"}}
                matching_laws = await laws_collection.find(
                    law_regex, {"law_id": 1, "title": 1}
                ).to_list(length=10)
                
                if matching_laws:
                    # 过滤旧版本，保留最新版
                    law_by_base = {}
                    for law in matching_laws:
                        base_name = _get_law_base_name(law["title"])
                        year = _get_law_year(law["title"])
                        if base_name not in law_by_base or year > law_by_base[base_name]["year"]:
                            law_by_base[base_name] = {"law": law, "year": year}
                    
                    latest_laws = [v["law"] for v in law_by_base.values()]
                    law_ids = [law["law_id"] for law in latest_laws]
                    article_query["law_id"] = {"$in": law_ids}
                    print(f"[AI Service] 匹配到法律: {[l['title'] for l in latest_laws]}")
        
        # 匹配条号
        chinese_num = law_service._arabic_to_chinese(article_num)
        article_query["article_display"] = {"$regex": f"^第{chinese_num}条", "$options": "i"}
        
        articles = await articles_collection.find(article_query).sort("article_num", 1).limit(top_k).to_list(length=top_k)
        
        if articles:
            # 获取法律标题
            law_ids_in_results = list(set(a.get("law_id") for a in articles if a.get("law_id")))
            laws_map = {}
            if law_ids_in_results:
                laws_cursor = laws_collection.find({"law_id": {"$in": law_ids_in_results}}, {"law_id": 1, "title": 1})
                async for law in laws_cursor:
                    laws_map[law["law_id"]] = law["title"]
            
            items = []
            for article in articles:
                items.append({
                    "law_id": article.get("law_id"),
                    "law_title": laws_map.get(article.get("law_id"), ""),
                    "article_num": article.get("article_num"),
                    "article_display": article.get("article_display", ""),
                    "content": article.get("content", ""),
                })
            
            print(f"[AI Service] 精准条号查找成功，返回 {len(items)} 条")
            return await _filter_and_format_results(items, keywords, top_k)
    
    # ========== 步骤 2: 标题匹配（如果提供了 law_name）==========
    law_ids = None
    if law_name:
        if _looks_like_law_name(law_name):
            law_name_pattern = law_name.replace("中华人民共和国", "").strip()
            law_regex = {"title": {"$regex": law_name_pattern, "$options": "i"}}
            
            matching_laws = await laws_collection.find(
                law_regex, {"law_id": 1, "title": 1}
            ).to_list(length=10)
            
            if matching_laws:
                print(f"[AI Service] 匹配到 {len(matching_laws)} 部法律: {[l['title'] for l in matching_laws]}")
                
                # 过滤旧版本法律，只保留最新版
                law_by_base = {}
                for law in matching_laws:
                    base_name = _get_law_base_name(law["title"])
                    year = _get_law_year(law["title"])
                    if base_name not in law_by_base or year > law_by_base[base_name]["year"]:
                        law_by_base[base_name] = {"law": law, "year": year}
                
                latest_laws = [v["law"] for v in law_by_base.values()]
                print(f"[AI Service] 过滤后保留最新版本: {[l['title'] for l in latest_laws]}")
                
                law_ids = [law["law_id"] for law in latest_laws]
    
    # ========== 步骤 3: 向量搜索（主要检索方式）==========
    vector_items = []
    vector_enabled = os.getenv("VECTOR_SEARCH_ENABLED", "true").lower() == "true"
    
    if vector_enabled:
        print(f"[AI Service] 尝试向量语义搜索: '{keywords}'")
        try:
            vector_items = await law_service.vector_search_for_rag(keywords, top_k=top_k * 3)
            
            # 应用相似度阈值过滤
            if vector_items:
                original_count = len(vector_items)
                vector_items = [item for item in vector_items if item.get("similarity", 0) >= MIN_SIMILARITY]
                if original_count > len(vector_items):
                    print(f"[AI Service] 相似度过滤: {original_count} -> {len(vector_items)} (阈值: {MIN_SIMILARITY})")
            
            # 如果有 law_ids 限制，过滤结果
            if vector_items and law_ids:
                original_count = len(vector_items)
                vector_items = [item for item in vector_items if item.get("law_id") in law_ids]
                print(f"[AI Service] 法律范围过滤: {original_count} -> {len(vector_items)}")
            
            if vector_items:
                print(f"[AI Service] 向量搜索成功，返回 {len(vector_items)} 条结果")
                print(f"[AI Service]    最高相似度: {vector_items[0].get('similarity', 0):.4f} - {vector_items[0].get('law_title', '')} {vector_items[0].get('article_display', '')}")
        except Exception as e:
            print(f"[AI Service] ⚠️ 向量搜索异常: {e}")
            vector_items = []
    else:
        print(f"[AI Service] 向量搜索未启用")
    
    # ========== 步骤 4: 关键词正则搜索（兜底补充）==========
    keyword_items = []
    print(f"[AI Service] 关键词正则搜索: '{keywords}'")
    
    article_query = {"content": {"$regex": keywords, "$options": "i"}}
    if law_ids:
        article_query["law_id"] = {"$in": law_ids}
    
    articles = await articles_collection.find(article_query).sort("article_num", 1).limit(top_k * 2).to_list(length=top_k * 2)
    
    if articles:
        # 获取法律标题
        law_ids_in_results = list(set(a.get("law_id") for a in articles if a.get("law_id")))
        laws_map = {}
        if law_ids_in_results:
            laws_cursor = laws_collection.find({"law_id": {"$in": law_ids_in_results}}, {"law_id": 1, "title": 1})
            async for law in laws_cursor:
                laws_map[law["law_id"]] = law["title"]
        
        for article in articles:
            keyword_items.append({
                "law_id": article.get("law_id"),
                "law_title": laws_map.get(article.get("law_id"), ""),
                "article_num": article.get("article_num"),
                "article_display": article.get("article_display", ""),
                "content": article.get("content", ""),
            })
        print(f"[AI Service] 关键词搜索找到 {len(keyword_items)} 条结果")
    
    # ========== 步骤 5: 合并去重 ==========
    # 以 (law_id, article_num, article_display) 为key去重
    seen = set()
    merged_items = []
    
    # 优先使用向量搜索结果（相关性更高）
    for item in vector_items:
        key = (item.get("law_id"), item.get("article_num"), item.get("article_display"))
        if key not in seen:
            seen.add(key)
            merged_items.append(item)
    
    # 补充关键词搜索结果
    for item in keyword_items:
        key = (item.get("law_id"), item.get("article_num"), item.get("article_display"))
        if key not in seen:
            seen.add(key)
            merged_items.append(item)
    
    # 限制返回数量
    merged_items = merged_items[:top_k * 2]
    
    print(f"[AI Service] 合并后共 {len(merged_items)} 条结果")
    
    if not merged_items:
        return {
            "found": False,
            "message": f"未检索到与'{keywords}'相关的法规条文",
            "articles": []
        }
    
    return await _filter_and_format_results(merged_items, keywords, top_k)


async def _filter_and_format_results(
    items: List[Dict[str, Any]],
    keywords: str,
    top_k: int,
) -> Dict[str, Any]:
    """
    过滤旧版本法规并格式化结果
    """
    import re
    
    def extract_base_name_and_year(title: str) -> tuple:
        """从标题中提取基础法规名和年份"""
        year_pattern = r'[（\(](\d{4})年[修订正]+[）\)]'
        match = re.search(year_pattern, title)
        if match:
            year = int(match.group(1))
            base_name = re.sub(year_pattern, '', title).strip()
        else:
            year = 0
            base_name = title
        return base_name, year
    
    # 按 (法规基础名, 条号) 分组，保留最新版本
    grouped = {}
    for item in items:
        law_title = item.get("law_title", "")
        article_display = item.get("article_display", "")
        base_name, year = extract_base_name_and_year(law_title)
        key = (base_name, article_display)
        
        if key not in grouped or year > grouped[key]["year"]:
            grouped[key] = {
                "item": item,
                "year": year
            }
    
    # 提取过滤后的结果
    filtered_items = [v["item"] for v in grouped.values()][:top_k]
    
    # 格式化结果
    articles = []
    for item in filtered_items:
        law_title = item.get("law_title", "")
        article_display = item.get("article_display", "")
        content = item.get("content", "")
        articles.append({
            "law_title": law_title,
            "article_display": article_display,
            "content": content[:1500] if len(content) > 1500 else content,
        })
    
    return {
        "found": len(articles) > 0,
        "message": f"检索到 {len(articles)} 条相关法规" if articles else f"未检索到与'{keywords}'相关的法规条文",
        "articles": articles
    }


def _build_messages_with_tools(
    message: str,
    history: Optional[list],
) -> List[Dict[str, str]]:
    """构建带工具调用的消息列表"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    return messages


def _build_messages_with_context(
    message: str,
    history: Optional[list],
    tool_result: str,
) -> List[Dict[str, str]]:
    """构建带工具结果的消息列表（用于第二轮调用）"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # 添加检索到的法规上下文
    messages.append({
        "role": "system",
        "content": f"以下为检索到的法规条文：\n{tool_result}\n\n请基于上述法规内容回答用户问题。"
    })
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    return messages


async def _call_llm(
    api_url: str,
    api_key: str,
    model: str,
    messages: List[Dict],
    skip_ssl_verify: bool,
    tools: Optional[List[Dict]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """调用 LLM API"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 4000,
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = {"type": "function", "function": {"name": "search_legal_knowledge"}}
    
    async with httpx.AsyncClient(timeout=timeout, verify=not skip_ssl_verify) as client:
        response = await client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def _format_tool_result(result: Dict[str, Any]) -> str:
    """格式化工具调用结果为人类可读的文本"""
    if not result.get("found"):
        return result.get("message", "未检索到相关法规")
    
    articles = result.get("articles", [])
    if not articles:
        return "未检索到相关法规"
    
    formatted = []
    for i, article in enumerate(articles, 1):
        law_title = article.get("law_title", "")
        article_display = article.get("article_display", "")
        content = article.get("content", "")
        formatted.append(f"[{i}] 《{law_title}》{article_display}：{content}")
    
    return "\n\n".join(formatted)


async def chat_with_ai(
    message: str,
    history: Optional[list] = None,
    db: AsyncIOMotorDatabase = None,
    use_rag: bool = True,
    rag_top_k: Optional[int] = None,
) -> Dict[str, Any]:
    """
    与 AI 进行对话（支持 Function Calling）
    
    流程：
    1. 第一轮：发送用户问题 + 工具定义，让 AI 决定是否调用工具
    2. 如果 AI 调用工具：执行检索，获取结果
    3. 第二轮：将检索结果作为上下文，让 AI 生成最终回答
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
            "use_function_calling": True,
        }
    
    api_url = config.get("api_url", DEFAULT_API_URL)
    if not api_url:
        raise Exception("AI 服务未配置 API URL，请在后台管理页面配置")
    
    api_key = config.get("api_key", DEFAULT_API_KEY) or ""
    model = config.get("model_name", DEFAULT_MODEL)
    skip_ssl_verify = config.get("skip_ssl_verify", False)
    provider_id = config.get("provider", "default")
    use_function_calling = config.get("use_function_calling", True)
    top_k = rag_top_k if rag_top_k is not None else config.get("rag_top_k", 6)
    
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    rag_sources = []
    
    try:
        if use_rag and use_function_calling and db is not None:
            # ========== Function Calling 模式 ==========
            print(f"[AI Service] Function Calling 模式启用")
            
            # 第一轮：让 AI 决定是否需要检索
            messages = _build_messages_with_tools(message, history)
            
            try:
                data = await _call_llm(
                    api_url, api_key, model, messages, skip_ssl_verify,
                    tools=[LEGAL_SEARCH_TOOL]
                )
                print(f"[AI Service] LLM 响应: tool_calls={data.get('choices', [{}])[0].get('message', {}).get('tool_calls')}")
            except httpx.HTTPStatusError as e:
                # 如果 API 不支持 tools 参数，回退到普通模式
                print(f"[AI Service] HTTP 错误 {e.response.status_code}，回退到普通模式")
                if e.response.status_code == 400:
                    return await _fallback_chat(
                        message, history, db, config, top_k
                    )
                raise
            
            # 累计 token 使用
            usage = data.get("usage", {})
            total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            total_usage["total_tokens"] += usage.get("total_tokens", 0)
            
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            
            # 检查是否有工具调用
            tool_calls = msg.get("tool_calls")
            
            if tool_calls:
                # AI 决定调用工具
                print(f"[AI Service] AI 调用了工具: {len(tool_calls)} 个")
                
                # 追加 assistant 消息（包含 tool_calls）到原始消息列表
                messages.append(msg)
                
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    func_name = func.get("name")
                    
                    if func_name == "search_legal_knowledge":
                        # 解析参数
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        
                        keywords = args.get("keywords", message)
                        law_name = args.get("law_name")
                        article_num = args.get("article_num")
                        
                        print(f"[AI Service] 工具参数: keywords='{keywords}', law_name='{law_name}', article_num={article_num}")
                        
                        # 执行检索
                        result = await execute_search_legal_knowledge(
                            db, keywords, law_name, article_num, top_k
                        )
                        
                        print(f"[AI Service] 检索结果: found={result.get('found')}, articles_count={len(result.get('articles', []))}")
                        
                        # 记录来源
                        for article in result.get("articles", []):
                            rag_sources.append({
                                "law_title": article.get("law_title", ""),
                                "article_display": article.get("article_display", ""),
                            })
                        
                        tool_result_text = _format_tool_result(result)
                        
                        # 追加 tool 消息（标准 Function Calling 格式）
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result_text
                        })
                
                # 第二轮：使用标准 Function Calling 消息格式，不带 tools 参数
                print(f"[AI Service] 第二轮调用，消息数: {len(messages)}")
                data2 = await _call_llm(
                    api_url, api_key, model, messages, skip_ssl_verify
                )
                
                # 累计 token 使用
                usage2 = data2.get("usage", {})
                total_usage["prompt_tokens"] += usage2.get("prompt_tokens", 0)
                total_usage["completion_tokens"] += usage2.get("completion_tokens", 0)
                total_usage["total_tokens"] += usage2.get("total_tokens", 0)
                
                reply = data2.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                # AI 直接回答（不需要检索）
                reply = msg.get("content", "")
        else:
            # ========== 普通模式（不使用 Function Calling）==========
            return await _fallback_chat(message, history, db, config, top_k)
        
        return {
            "reply": reply or "抱歉，未能生成回答。",
            "usage": total_usage,
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


async def _fallback_chat(
    message: str,
    history: Optional[list],
    db: AsyncIOMotorDatabase,
    config: dict,
    top_k: int,
) -> Dict[str, Any]:
    """
    回退模式：使用传统 RAG 方式（适用于不支持 Function Calling 的模型）
    """
    from app.services.knowledge_base_service import KnowledgeBaseService
    
    api_url = config.get("api_url", DEFAULT_API_URL)
    api_key = config.get("api_key", DEFAULT_API_KEY) or ""
    model = config.get("model_name", DEFAULT_MODEL)
    skip_ssl_verify = config.get("skip_ssl_verify", False)
    provider_id = config.get("provider", "default")
    
    rag_context = ""
    rag_sources = []
    
    if db is not None:
        kb_service = KnowledgeBaseService(db)
        rag_data = await kb_service.retrieve(message, top_k=top_k)
        rag_context = rag_data.get("context", "")
        rag_sources = rag_data.get("sources", [])
        direct_answer = rag_data.get("direct_answer", "")
        
        if direct_answer:
            return {
                "reply": direct_answer,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "provider": "knowledge_base",
                "sources": rag_sources,
            }
    
    # 构建消息
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if rag_context:
        messages.append({
            "role": "system",
            "content": f"以下为可引用的法规条文摘要：\n{rag_context}\n\n回答时应优先引用上述条文。"
        })
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    
    data = await _call_llm(api_url, api_key, model, messages, skip_ssl_verify)
    
    reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    
    return {
        "reply": reply or "抱歉，未能生成回答。",
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
        "provider": provider_id,
        "sources": rag_sources,
    }
