"""
笔录管理服务层 — CRUD + AI 分析 + 知识库沉淀
"""
import json
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.db import COLLECTION_CASES, COLLECTION_TRANSCRIPTS
from app.services.embedding_client import get_embeddings


class TranscriptService:
    """笔录管理 + AI 分析 + 知识库"""

    def __init__(self, db: Any):
        self.db = db
        self.cases = db[COLLECTION_CASES]
        self.transcripts = db[COLLECTION_TRANSCRIPTS]

    # ==================== CRUD ====================

    async def create_transcript(self, case_id: str, data: dict) -> dict:
        """创建笔录（文本方式）"""
        # 确认案件存在
        case = await self.cases.find_one({"case_id": case_id})
        if not case:
            raise ValueError(f"案件不存在: {case_id}")

        now = datetime.utcnow()
        doc = {
            "transcript_id": str(uuid.uuid4()),
            "case_id": case_id,
            "title": data["title"],
            "type": data["type"],
            "subject_name": data["subject_name"],
            "subject_role": data["subject_role"],
            "content": data["content"],
            "file_name": data.get("file_name", ""),
            "analysis": None,
            "embedding": None,
            "keywords": [],
            "analysis_status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        await self.transcripts.insert_one(doc)
        # 更新案件笔录计数
        await self.cases.update_one(
            {"case_id": case_id},
            {"$inc": {"transcript_count": 1}, "$set": {"updated_at": now}}
        )
        doc.pop("_id", None)
        return doc

    async def get_transcript_list(self, case_id: str) -> List[dict]:
        """获取案件下所有笔录列表"""
        cursor = self.transcripts.find(
            {"case_id": case_id},
            {
                "_id": 0,
                "content": 0,          # 列表不返回全文
                "embedding": 0,
            }
        ).sort("created_at", -1)
        items = await cursor.to_list(length=200)
        # 简化分析结果
        for item in items:
            analysis = item.get("analysis")
            if analysis:
                item["summary"] = analysis.get("summary", "")
                laws = analysis.get("related_laws", [])
                item["related_laws_display"] = [
                    f"《{l.get('law_title', '')}》{l.get('article_display', '')}"
                    for l in laws[:3]
                ]
                # 列表不返回完整分析
                del item["analysis"]
            else:
                item["summary"] = None
                item["related_laws_display"] = []
        return items

    async def get_transcript_detail(self, case_id: str, transcript_id: str) -> Optional[dict]:
        """获取笔录详情（含分析结果）"""
        doc = await self.transcripts.find_one(
            {"case_id": case_id, "transcript_id": transcript_id},
            {"_id": 0, "embedding": 0}
        )
        return doc

    async def delete_transcript(self, case_id: str, transcript_id: str) -> bool:
        """删除笔录"""
        result = await self.transcripts.delete_one(
            {"case_id": case_id, "transcript_id": transcript_id}
        )
        if result.deleted_count > 0:
            await self.cases.update_one(
                {"case_id": case_id},
                {"$inc": {"transcript_count": -1}, "$set": {"updated_at": datetime.utcnow()}}
            )
            return True
        return False

    async def get_analysis_status(self, case_id: str, transcript_id: str) -> Optional[str]:
        """查询分析状态"""
        doc = await self.transcripts.find_one(
            {"case_id": case_id, "transcript_id": transcript_id},
            {"_id": 0, "analysis_status": 1}
        )
        return doc.get("analysis_status") if doc else None

    # ==================== 文件解析 ====================

    @staticmethod
    def parse_docx(file_bytes: bytes) -> str:
        """解析 DOCX 文件内容"""
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except ImportError:
            raise RuntimeError("python-docx 未安装，无法解析 DOCX 文件")
        except Exception as e:
            raise RuntimeError(f"DOCX 解析失败: {e}")

    @staticmethod
    def parse_txt(file_bytes: bytes) -> str:
        """解析 TXT 文件内容"""
        for encoding in ["utf-8", "gbk", "gb2312", "utf-16"]:
            try:
                return file_bytes.decode(encoding)
            except (UnicodeDecodeError, Exception):
                continue
        raise RuntimeError("无法识别文件编码")

    # ==================== AI 分析 ====================

    async def analyze_transcript(self, case_id: str, transcript_id: str):
        """
        触发笔录 AI 分析（异步后台任务）
        分析完成后自动执行知识库沉淀（关键词提取 + 向量化）
        """
        # 更新状态为 analyzing
        await self.transcripts.update_one(
            {"case_id": case_id, "transcript_id": transcript_id},
            {"$set": {"analysis_status": "analyzing", "updated_at": datetime.utcnow()}}
        )

        try:
            # 获取笔录全文
            doc = await self.transcripts.find_one(
                {"case_id": case_id, "transcript_id": transcript_id},
                {"_id": 0, "content": 1, "title": 1, "type": 1,
                 "subject_name": 1, "subject_role": 1}
            )
            if not doc:
                raise ValueError("笔录不存在")

            content = doc["content"]

            # 调用 LLM 分析
            analysis_result = await self._call_llm_analyze(doc)

            # 提取关键词（从分析结果中）
            keywords = self._extract_keywords(analysis_result)

            # 保存分析结果
            update_data: Dict[str, Any] = {
                "analysis": analysis_result,
                "analysis_status": "analyzed",
                "keywords": keywords,
                "updated_at": datetime.utcnow(),
            }

            # 知识库沉淀：向量化摘要
            summary_text = analysis_result.get("summary", "")
            if summary_text:
                try:
                    embeddings = await get_embeddings([summary_text])
                    if embeddings and len(embeddings) > 0:
                        update_data["embedding"] = embeddings[0]
                        print(f"[TranscriptService] ✅ 笔录向量化完成: {transcript_id}")
                    else:
                        print(f"[TranscriptService] ⚠️ 向量化返回空，跳过")
                except Exception as e:
                    print(f"[TranscriptService] ⚠️ 向量化失败（不影响分析结果）: {e}")

            await self.transcripts.update_one(
                {"case_id": case_id, "transcript_id": transcript_id},
                {"$set": update_data}
            )
            print(f"[TranscriptService] ✅ 笔录分析完成: {transcript_id}")

        except Exception as e:
            print(f"[TranscriptService] ❌ 笔录分析失败: {e}")
            await self.transcripts.update_one(
                {"case_id": case_id, "transcript_id": transcript_id},
                {"$set": {
                    "analysis_status": "failed",
                    "updated_at": datetime.utcnow(),
                }}
            )

    async def _call_llm_analyze(self, doc: dict) -> dict:
        """调用 LLM 执行笔录结构化分析"""
        import httpx
        from app.services.ai_service import get_ai_config, LLM_TIMEOUT

        config = await get_ai_config(self.db)
        api_url = config["api_url"]
        api_key = config["api_key"]
        model_name = config["model_name"]
        skip_ssl = config.get("skip_ssl_verify", False)

        system_prompt = self._build_analysis_system_prompt()
        user_prompt = self._build_analysis_user_prompt(doc)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 6000,
        }

        # 使用较长超时（笔录分析输出较多）
        analysis_timeout = httpx.Timeout(
            connect=30.0, read=300.0, write=30.0, pool=30.0
        )

        async with httpx.AsyncClient(verify=not skip_ssl, timeout=analysis_timeout) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

        content = result["choices"][0]["message"]["content"]

        # 解析 JSON 结果
        analysis = self._parse_analysis_json(content)
        return analysis

    def _build_analysis_system_prompt(self) -> str:
        """构建笔录分析系统提示词"""
        return """你是一名专业的公安执法辅助分析员，擅长从询问/讯问笔录中提取结构化信息。

你的任务是对笔录内容进行全面分析，提取以下要素并以 JSON 格式返回：

1. **persons** (涉及人员)：提取所有出现的人物，包括姓名、角色(嫌疑人/被害人/证人/询问人)、身份证号、联系方式、特征描述
2. **timeline** (时间线)：按时间顺序提取事件，包括时间描述、事件内容、原文引用
3. **locations** (地点)：提取所有涉及的地点，标注类型(事发地/报案地/询问地)
4. **key_facts** (关键事实)：提取核心事实，分类为(行为/动机/后果/工具)，附原文引用
5. **items_amounts** (涉案物品/金额)：提取物品名称、数量、价值
6. **related_laws** (关联法条)：根据笔录内容分析可能适用的法律条文，标注置信度(high/medium/low)
7. **compliance_issues** (规范性检查)：检查笔录是否符合办案规范，如权利告知、签名、录音录像等
8. **summary** (分析摘要)：200-500字的综合摘要

【输出格式要求】
必须返回严格的 JSON 格式，不要包含 markdown 代码块标记。直接返回 JSON 对象。

JSON 结构如下：
{
  "persons": [{"name": "", "role": "", "id_number": "", "contact": "", "description": ""}],
  "timeline": [{"time": "", "event": "", "source": ""}],
  "locations": [{"name": "", "type": "", "detail": ""}],
  "key_facts": [{"description": "", "category": "", "source": ""}],
  "items_amounts": [{"name": "", "quantity": "", "value": ""}],
  "related_laws": [{"law_title": "", "article_display": "", "relevance": "", "confidence": "high/medium/low"}],
  "compliance_issues": [{"item": "", "status": "pass/warning/fail", "detail": ""}],
  "summary": ""
}

【注意事项】
- 时间线必须按时间先后排序
- 关联法条要基于事实分析，不要凭空推测
- 规范性检查应检查：权利义务告知、询问人数、笔录起止时间、签名、同步录音录像等
- 原文引用尽量精简，摘取关键语句即可
- 如果某项信息在笔录中未提及，返回空数组即可
- summary 应覆盖案情概要、关键证据、法律适用建议"""

    def _build_analysis_user_prompt(self, doc: dict) -> str:
        """构建用户提示词"""
        return f"""请分析以下笔录内容：

【笔录标题】{doc.get('title', '')}
【笔录类型】{doc.get('type', '')}
【被询问/讯问人】{doc.get('subject_name', '')}（{doc.get('subject_role', '')}）

【笔录全文】
{doc.get('content', '')}

请按照系统指令要求，返回结构化的 JSON 分析结果。"""

    def _parse_analysis_json(self, content: str) -> dict:
        """解析 LLM 返回的 JSON 分析结果"""
        # 去除 markdown 代码块标记
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # 去掉 ```json 或 ``` 开头
            lines = cleaned.split("\n")
            start = 1
            end = len(lines) - 1
            if lines[-1].strip() == "```":
                end = -1
            cleaned = "\n".join(lines[start:end]).strip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                try:
                    result = json.loads(match.group())
                except json.JSONDecodeError:
                    result = {"summary": content, "parse_error": True}
            else:
                result = {"summary": content, "parse_error": True}

        # 确保所有必需字段存在
        defaults = {
            "persons": [], "timeline": [], "locations": [],
            "key_facts": [], "items_amounts": [], "related_laws": [],
            "compliance_issues": [], "summary": "",
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default

        return result

    def _extract_keywords(self, analysis: dict) -> List[str]:
        """从分析结果中提取关键词（用于全文检索）"""
        keywords = set()

        # 从人员中提取
        for p in analysis.get("persons", []):
            if p.get("name"):
                keywords.add(p["name"])

        # 从关键事实中提取
        for f in analysis.get("key_facts", []):
            if f.get("category"):
                keywords.add(f["category"])

        # 从关联法条中提取
        for l in analysis.get("related_laws", []):
            if l.get("law_title"):
                keywords.add(l["law_title"])

        # 从地点中提取
        for loc in analysis.get("locations", []):
            if loc.get("name"):
                keywords.add(loc["name"])

        return list(keywords)

    # ==================== 交叉分析（二期） ====================

    async def get_cross_analysis_status(self, case_id: str) -> Optional[dict]:
        """获取交叉分析状态和结果"""
        case = await self.cases.find_one(
            {"case_id": case_id},
            {"_id": 0, "cross_analysis": 1}
        )
        if not case:
            return None
        # 案件存在但未做过交叉分析时，返回 not_started 状态
        return case.get("cross_analysis") or {"analysis_status": "not_started"}

    async def cross_analyze(self, case_id: str):
        """
        触发交叉分析（异步后台任务）
        分步策略：
        1. 拼接各笔录分析摘要 + 时间线 + 关键事实
        2. LLM 发现矛盾点、评估一致性
        3. 针对矛盾点提取原文段落做详细比对
        """
        # 标记分析中
        await self.cases.update_one(
            {"case_id": case_id},
            {"$set": {
                "cross_analysis": {
                    "analysis_status": "analyzing",
                    "analyzed_at": datetime.utcnow(),
                },
                "updated_at": datetime.utcnow(),
            }}
        )

        try:
            # 获取案件下所有已分析的笔录
            cursor = self.transcripts.find(
                {"case_id": case_id, "analysis_status": "analyzed"},
                {"_id": 0, "transcript_id": 1, "title": 1, "content": 1,
                 "subject_name": 1, "subject_role": 1, "type": 1, "analysis": 1}
            )
            transcripts = await cursor.to_list(length=100)

            if len(transcripts) < 2:
                raise ValueError("至少需要 2 份已分析的笔录才能交叉分析")

            # === 第 1 步：拼接要素摘要，发现矛盾 + 一致性评分 ===
            cross_result = await self._cross_step1_compare(transcripts)

            # === 第 2 步：针对矛盾点从原文提取详细引用 ===
            if cross_result.get("contradictions"):
                cross_result = await self._cross_step2_enrich(transcripts, cross_result)

            # 保存结果
            cross_result["analysis_status"] = "analyzed"
            cross_result["analyzed_at"] = datetime.utcnow()

            await self.cases.update_one(
                {"case_id": case_id},
                {"$set": {
                    "cross_analysis": cross_result,
                    "updated_at": datetime.utcnow(),
                }}
            )
            print(f"[TranscriptService] ✅ 交叉分析完成: {case_id}")

        except Exception as e:
            print(f"[TranscriptService] ❌ 交叉分析失败: {e}")
            await self.cases.update_one(
                {"case_id": case_id},
                {"$set": {
                    "cross_analysis": {
                        "analysis_status": "failed",
                        "error": str(e),
                        "analyzed_at": datetime.utcnow(),
                    },
                    "updated_at": datetime.utcnow(),
                }}
            )

    async def _cross_step1_compare(self, transcripts: List[dict]) -> dict:
        """
        交叉分析第 1 步：拼接各笔录分析摘要 → 发现矛盾 + 一致性评分
        """
        import httpx
        from app.services.ai_service import get_ai_config

        config = await get_ai_config(self.db)
        api_url = config["api_url"]
        api_key = config["api_key"]
        model_name = config["model_name"]
        skip_ssl = config.get("skip_ssl_verify", False)

        # 拼接各笔录的分析摘要
        summaries = []
        for t in transcripts:
            analysis = t.get("analysis", {})
            entry = f"【{t['title']}】（{t['subject_name']}，{t['subject_role']}）\n"
            entry += f"摘要：{analysis.get('summary', '无')}\n"

            timeline = analysis.get("timeline", [])
            if timeline:
                entry += "时间线：\n"
                for ev in timeline:
                    entry += f"  - {ev.get('time', '')}: {ev.get('event', '')}\n"

            facts = analysis.get("key_facts", [])
            if facts:
                entry += "关键事实：\n"
                for f in facts:
                    entry += f"  - [{f.get('category', '')}] {f.get('description', '')}\n"

            persons = analysis.get("persons", [])
            if persons:
                entry += "涉及人员：\n"
                for p in persons:
                    entry += f"  - {p.get('name', '')}（{p.get('role', '')}）: {p.get('description', '')}\n"

            summaries.append(entry)

        combined_text = "\n---\n".join(summaries)

        system_prompt = """你是一名专业的公安案件分析员，擅长对多份笔录进行交叉比对分析。

你需要分析以下多份笔录的分析摘要，完成以下任务：

1. **发现矛盾点（contradictions）**：找出不同笔录之间在时间、事实、数量、细节等方面的矛盾
2. **构建统一时间线（unified_timeline）**：将各笔录的时间线合并，标注哪些事件各方一致、哪些有异议
3. **梳理证据链（evidence_chain）**：归纳已有的证据类型，标注哪些需要补充
4. **评估一致性（consistency_score）**：给出 0-100 的整体一致性评分
5. **总结（summary）**：综合分析摘要

【输出格式】
返回严格的 JSON 格式，不要包含 markdown 代码块标记。

{
  "contradictions": [
    {
      "type": "时间矛盾/事实矛盾/数量矛盾/细节矛盾",
      "severity": "high/medium/low",
      "description": "矛盾描述",
      "sources": [
        {"transcript_id": "", "person": "某某", "quote": "相关陈述摘要"}
      ]
    }
  ],
  "unified_timeline": [
    {
      "time": "时间描述",
      "event": "事件描述",
      "agreed_by": ["一致的笔录人"],
      "disputed_by": ["有异议的笔录人"]
    }
  ],
  "evidence_chain": [
    {
      "type": "言证/物证/书证/电子证据",
      "description": "证据描述",
      "status": "已获取/待补充",
      "source_transcripts": ["来源笔录标题"]
    }
  ],
  "consistency_score": 0,
  "summary": ""
}

【注意】
- 矛盾点按严重程度排序（high > medium > low）
- 时间线按时间先后排序
- consistency_score：完全一致=100，矛盾越多越低
- 如果没有发现矛盾，contradictions 为空数组，consistency_score 应较高
- sources 中的 person 填写笔录中的被询问人姓名"""

        user_prompt = f"""以下是同一案件中 {len(transcripts)} 份笔录的分析摘要，请进行交叉比对分析：

{combined_text}

请返回 JSON 格式的交叉分析结果。"""

        # 构建笔录标题→ID映射，供后续引用
        title_id_map = {t["title"]: t["transcript_id"] for t in transcripts}
        name_id_map = {t["subject_name"]: t["transcript_id"] for t in transcripts}

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 6000,
        }

        analysis_timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)

        async with httpx.AsyncClient(verify=not skip_ssl, timeout=analysis_timeout) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

        content = result["choices"][0]["message"]["content"]
        cross_result = self._parse_analysis_json(content)

        # 补充 transcript_id（LLM 可能只返回人名，需要映射）
        for c in cross_result.get("contradictions", []):
            for src in c.get("sources", []):
                if not src.get("transcript_id"):
                    person = src.get("person", "")
                    src["transcript_id"] = name_id_map.get(person, "")

        return cross_result

    async def _cross_step2_enrich(self, transcripts: List[dict], cross_result: dict) -> dict:
        """
        交叉分析第 2 步：针对每个矛盾点，从原始笔录提取相关段落做详细比对
        """
        import httpx
        from app.services.ai_service import get_ai_config

        config = await get_ai_config(self.db)
        api_url = config["api_url"]
        api_key = config["api_key"]
        model_name = config["model_name"]
        skip_ssl = config.get("skip_ssl_verify", False)

        contradictions = cross_result.get("contradictions", [])
        if not contradictions:
            return cross_result

        # 拼接所有矛盾点描述
        contra_texts = []
        for i, c in enumerate(contradictions, 1):
            persons = ", ".join(s.get("person", "") for s in c.get("sources", []))
            contra_texts.append(f"矛盾 {i}: [{c.get('type', '')}] {c.get('description', '')}（涉及: {persons}）")

        # 拼接各笔录原文的关键段落（控制总 token 量）
        transcript_excerpts = []
        for t in transcripts:
            content = t.get("content", "")
            # 截取前 3000 字（避免超长）
            excerpt = content[:3000] if len(content) > 3000 else content
            transcript_excerpts.append(
                f"【{t['title']}】（{t['subject_name']}，{t['subject_role']}）\n{excerpt}"
            )

        system_prompt = """你是一名专业的公安案件分析员。现在需要你针对已发现的矛盾点，从原始笔录中提取准确的原文引用，以增强矛盾分析的可信度。

请对每个矛盾点：
1. 找到各方在原始笔录中的相关陈述
2. 提取关键原文引用（精简到 1-2 句话）
3. 重新评估矛盾的严重程度

【输出格式】
返回 JSON 数组，每个元素对应一个矛盾点（保持原顺序）：

[
  {
    "type": "矛盾类型",
    "severity": "high/medium/low",
    "description": "更精准的矛盾描述",
    "sources": [
      {"person": "某某", "quote": "精确的原文引用"}
    ]
  }
]

只返回 JSON 数组，不要包含 markdown 代码块标记。"""

        user_prompt = f"""已发现的矛盾点：
{chr(10).join(contra_texts)}

各份笔录原文（摘要）：
{"".join(transcript_excerpts)}

请从原文中提取准确引用，返回增强后的矛盾分析。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4000,
        }

        name_id_map = {t["subject_name"]: t["transcript_id"] for t in transcripts}

        analysis_timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)

        try:
            async with httpx.AsyncClient(verify=not skip_ssl, timeout=analysis_timeout) as client:
                response = await client.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            content = result["choices"][0]["message"]["content"]

            # 解析返回的矛盾点数组
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                start = 1
                end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                cleaned = "\n".join(lines[start:end]).strip()

            try:
                enriched = json.loads(cleaned)
            except json.JSONDecodeError:
                match = re.search(r'\[[\s\S]*\]', cleaned)
                if match:
                    try:
                        enriched = json.loads(match.group())
                    except json.JSONDecodeError:
                        enriched = None
                else:
                    enriched = None

            if enriched and isinstance(enriched, list):
                # 补充 transcript_id
                for c in enriched:
                    for src in c.get("sources", []):
                        if not src.get("transcript_id"):
                            person = src.get("person", "")
                            src["transcript_id"] = name_id_map.get(person, "")
                cross_result["contradictions"] = enriched

        except Exception as e:
            print(f"[TranscriptService] ⚠️ 矛盾点深入分析失败（保留原结果）: {e}")

        return cross_result

    # ==================== 知识库搜索 ====================

    async def search_transcripts(
        self,
        keyword: str,
        transcript_type: Optional[str] = None,
        subject_role: Optional[str] = None,
        case_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """全局搜索笔录知识库（跨案件）"""
        import re as _re
        safe_kw = _re.escape(keyword)

        # 构建搜索条件
        query: Dict[str, Any] = {
            "$or": [
                {"content": {"$regex": safe_kw, "$options": "i"}},
                {"keywords": {"$regex": safe_kw, "$options": "i"}},
                {"analysis.summary": {"$regex": safe_kw, "$options": "i"}},
                {"title": {"$regex": safe_kw, "$options": "i"}},
            ]
        }
        if transcript_type:
            query["type"] = transcript_type
        if subject_role:
            query["subject_role"] = subject_role

        # 如果按案件类型筛选，需要先查出符合的案件ID
        if case_type:
            case_ids_cursor = self.cases.find(
                {"case_type": case_type}, {"case_id": 1, "_id": 0}
            )
            case_ids = [c["case_id"] async for c in case_ids_cursor]
            if not case_ids:
                return {"items": [], "total": 0, "page": page,
                        "page_size": page_size, "total_pages": 0}
            query["case_id"] = {"$in": case_ids}

        total = await self.transcripts.count_documents(query)
        skip = (page - 1) * page_size

        cursor = self.transcripts.find(
            query,
            {
                "_id": 0,
                "embedding": 0,
                "content": 0,  # 不返回全文，后面单独截取匹配片段
            }
        ).sort("created_at", -1).skip(skip).limit(page_size)

        raw_items = await cursor.to_list(length=page_size)

        # 高亮匹配内容（从原文截取匹配片段）
        items = []
        for item in raw_items:
            tid = item["transcript_id"]
            # 重新读取 content 做片段截取
            full_doc = await self.transcripts.find_one(
                {"transcript_id": tid}, {"_id": 0, "content": 1}
            )
            match_snippet = ""
            if full_doc and full_doc.get("content"):
                text = full_doc["content"]
                m = _re.search(safe_kw, text, _re.IGNORECASE)
                if m:
                    start = max(0, m.start() - 40)
                    end = min(len(text), m.end() + 40)
                    match_snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
            item["match_snippet"] = match_snippet

            # 附带案件名称
            case_doc = await self.cases.find_one(
                {"case_id": item.get("case_id")},
                {"_id": 0, "case_name": 1, "case_type": 1}
            )
            item["case_name"] = case_doc["case_name"] if case_doc else ""
            item["case_type_display"] = case_doc.get("case_type", "") if case_doc else ""

            # 简化分析字段
            analysis = item.pop("analysis", None)
            if analysis:
                item["summary"] = analysis.get("summary", "")
                laws = analysis.get("related_laws", [])
                item["related_laws_display"] = [
                    f"《{l.get('law_title', '')}》{l.get('article_display', '')}"
                    for l in laws[:3]
                ]
            else:
                item["summary"] = None
                item["related_laws_display"] = []

            items.append(item)

        total_pages = (total + page_size - 1) // page_size
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
