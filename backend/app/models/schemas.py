"""
Pydantic 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 法规相关模型 ====================

class LawBase(BaseModel):
    """法规基础模型"""
    law_id: str = Field(..., description="法规唯一标识")
    title: str = Field(..., description="法规标题")
    category: str = Field(..., description="法规分类")
    level: str = Field(..., description="效力层级")
    issue_org: str = Field(..., description="制定机关")
    issue_date: str = Field(..., description="发布日期")
    effect_date: str = Field(..., description="生效日期")
    status: str = Field(default="有效", description="效力状态")
    summary: Optional[str] = Field(None, description="法规摘要")
    tags: List[str] = Field(default_factory=list, description="标签")
    source_url: Optional[str] = Field(None, description="来源URL")


class Law(LawBase):
    """法规完整模型"""
    full_text: str = Field(..., description="法规全文")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "law_id": "criminal_procedure_law_2018",
                "title": "中华人民共和国刑事诉讼法",
                "category": "刑事法律",
                "level": "法律",
                "issue_org": "全国人民代表大会",
                "issue_date": "2018-10-26",
                "effect_date": "2019-01-01",
                "status": "有效",
                "summary": "规范刑事诉讼程序的基本法律",
                "tags": ["刑事", "诉讼"],
                "full_text": "第一编 总则\n第一章 任务和基本原则\n第一条 为了..."
            }
        }


class LawCreate(BaseModel):
    """创建法规请求模型"""
    title: str = Field(..., description="法规标题")
    category: str = Field(..., description="法规分类")
    level: str = Field(..., description="效力层级")
    issue_org: str = Field(..., description="制定机关")
    issue_date: str = Field(..., description="发布日期")
    effect_date: str = Field(..., description="生效日期")
    status: str = Field(default="有效", description="效力状态")
    summary: str = Field(default="", description="修订说明")
    articles: List[Dict[str, Any]] = Field(..., description="条文列表")

class LawListResponse(BaseModel):
    """法规列表响应"""
    law_id: str
    title: str
    category: str
    level: str
    issue_date: str
    effect_date: str
    status: str
    tags: List[str]


class Article(BaseModel):
    """法规条文模型"""
    law_id: str = Field(..., description="所属法规ID")
    article_num: int = Field(..., description="条号（数字）")
    article_display: str = Field(..., description="条号显示（如：第八十三条）")
    chapter: Optional[str] = Field(None, description="所属章")
    section: Optional[str] = Field(None, description="所属节")
    content: str = Field(..., description="条文内容")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "law_id": "criminal_procedure_law_2018",
                "article_num": 83,
                "article_display": "第八十三条",
                "chapter": "第二编 侦查",
                "section": "第四章 强制措施",
                "content": "公安机关拘留人的时候，必须出示拘留证...",
                "keywords": ["拘留", "拘留证", "强制措施"]
            }
        }


# ==================== 文书模板相关模型 ====================

class TemplateField(BaseModel):
    """模板字段定义"""
    name: str = Field(..., description="字段名称（变量名）")
    label: str = Field(..., description="字段标签（显示名）")
    type: str = Field(..., description="字段类型：text/textarea/select/date")
    options: Optional[List[str]] = Field(None, description="选项（用于select类型）")
    default: Optional[str] = Field(None, description="默认值")
    required: bool = Field(default=True, description="是否必填")


class DocTemplate(BaseModel):
    """文书模板模型"""
    template_id: str = Field(..., description="模板唯一标识")
    name: str = Field(..., description="模板名称")
    category: str = Field(..., description="模板分类")
    fields: List[TemplateField] = Field(..., description="字段定义")
    content: str = Field(..., description="模板内容（支持{{变量}}占位符）")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "arrest_warrant",
                "name": "拘留证",
                "category": "刑事办案",
                "fields": [
                    {"name": "suspect_name", "label": "犯罪嫌疑人姓名", "type": "text"},
                    {"name": "suspect_gender", "label": "性别", "type": "select", "options": ["男", "女"]},
                    {"name": "case_reason", "label": "案由", "type": "text"}
                ],
                "content": "兹因{{suspect_name}}涉嫌{{case_reason}}..."
            }
        }


class DocInstance(BaseModel):
    """文书实例模型"""
    template_id: str = Field(..., description="模板ID")
    field_values: Dict[str, Any] = Field(..., description="字段值")
    created_by: Optional[str] = Field(None, description="创建人")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== API 通用响应模型 ====================

class PaginationInfo(BaseModel):
    """分页信息"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


class APIResponse(BaseModel):
    """统一 API 响应"""
    success: bool = Field(default=True, description="是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    pagination: Optional[PaginationInfo] = Field(None, description="分页信息")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 搜索相关模型 ====================

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索关键字")
    law_id: Optional[str] = Field(None, description="限定法规ID（单法规内搜索）")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=500, description="每页大小")


class SearchResultItem(BaseModel):
    """搜索结果项"""
    law_id: str
    law_title: str
    law_category: Optional[str] = None
    article_num: Optional[int] = None
    article_display: Optional[str] = None
    content: str
    highlight: Optional[str] = None  # 高亮片段
    score: Optional[float] = None    # 相关性得分


# ==================== 案件相关模型 ====================

class CaseType(str, Enum):
    """案件类型"""
    ZHIAN = "治安案件"
    XINGSHI = "刑事案件"
    XINGZHENG = "行政案件"


class CaseStatus(str, Enum):
    """案件状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class CaseCreate(BaseModel):
    """创建案件请求"""
    case_name: str = Field(..., description="案件名称")
    case_number: Optional[str] = Field(None, description="案件编号")
    case_type: str = Field(..., description="案件类型")
    description: Optional[str] = Field(None, description="案件简述")
    tags: List[str] = Field(default_factory=list, description="标签")


class CaseUpdate(BaseModel):
    """更新案件请求"""
    case_name: Optional[str] = None
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CaseListItem(BaseModel):
    """案件列表项"""
    case_id: str
    case_name: str
    case_number: Optional[str] = None
    case_type: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    transcript_count: int = 0
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== 笔录相关模型 ====================

class TranscriptType(str, Enum):
    """笔录类型"""
    INQUIRY = "询问笔录"
    INTERROGATION = "讯问笔录"
    STATEMENT = "陈述笔录"
    IDENTIFICATION = "辨认笔录"


class SubjectRole(str, Enum):
    """被询问人角色"""
    SUSPECT = "嫌疑人"
    VICTIM = "被害人"
    WITNESS = "证人"
    REPORTER = "报案人"


class AnalysisStatus(str, Enum):
    """分析状态"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class TranscriptCreate(BaseModel):
    """创建笔录请求（文本方式）"""
    title: str = Field(..., description="笔录标题")
    type: str = Field(..., description="笔录类型")
    subject_name: str = Field(..., description="被询问人姓名")
    subject_role: str = Field(..., description="被询问人角色")
    content: str = Field(..., description="笔录全文")
    auto_analyze: bool = Field(default=True, description="是否自动触发AI分析")


class PersonInfo(BaseModel):
    """人员信息"""
    name: str = ""
    role: str = ""
    id_number: Optional[str] = None
    contact: Optional[str] = None
    description: Optional[str] = None


class TimelineEvent(BaseModel):
    """时间线事件"""
    time: str = ""
    event: str = ""
    source: Optional[str] = None


class LocationInfo(BaseModel):
    """地点信息"""
    name: str = ""
    type: str = ""
    detail: Optional[str] = None


class KeyFact(BaseModel):
    """关键事实"""
    description: str = ""
    category: str = ""
    source: Optional[str] = None


class ItemAmount(BaseModel):
    """涉案物品/金额"""
    name: str = ""
    quantity: Optional[str] = None
    value: Optional[str] = None


class RelatedLaw(BaseModel):
    """关联法条"""
    law_title: str = ""
    article_display: str = ""
    law_id: Optional[str] = None
    article_num: Optional[int] = None
    relevance: Optional[str] = None
    confidence: str = "medium"


class ComplianceIssue(BaseModel):
    """规范性检查项"""
    item: str = ""
    status: str = "pass"
    detail: Optional[str] = None


class TranscriptAnalysis(BaseModel):
    """笔录分析结果"""
    persons: List[PersonInfo] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    locations: List[LocationInfo] = Field(default_factory=list)
    key_facts: List[KeyFact] = Field(default_factory=list)
    items_amounts: List[ItemAmount] = Field(default_factory=list)
    related_laws: List[RelatedLaw] = Field(default_factory=list)
    compliance_issues: List[ComplianceIssue] = Field(default_factory=list)
    summary: str = ""


class TranscriptListItem(BaseModel):
    """笔录列表项"""
    transcript_id: str
    case_id: str
    title: str
    type: str
    subject_name: str
    subject_role: str
    analysis_status: str = "pending"
    summary: Optional[str] = None
    related_laws_display: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


# ==================== 交叉分析相关模型（二期） ====================

class ContradictionSource(BaseModel):
    """矛盾点来源"""
    transcript_id: str = ""
    person: str = ""
    quote: str = ""


class Contradiction(BaseModel):
    """矛盾点"""
    type: str = ""              # 时间矛盾 / 事实矛盾 / 数量矛盾 / 细节矛盾
    severity: str = "medium"    # high / medium / low
    description: str = ""
    sources: List[ContradictionSource] = Field(default_factory=list)


class UnifiedTimelineEvent(BaseModel):
    """统一时间线事件"""
    time: str = ""
    event: str = ""
    agreed_by: List[str] = Field(default_factory=list)     # 一致的笔录人
    disputed_by: List[str] = Field(default_factory=list)   # 有异议的笔录人


class EvidenceItem(BaseModel):
    """证据链条目"""
    type: str = ""               # 言证 / 物证 / 书证 / 电子证据
    description: str = ""
    status: str = "待补充"       # 已获取 / 待补充
    source_transcripts: List[str] = Field(default_factory=list)


class CrossAnalysisResult(BaseModel):
    """交叉分析结果"""
    contradictions: List[Contradiction] = Field(default_factory=list)
    unified_timeline: List[UnifiedTimelineEvent] = Field(default_factory=list)
    evidence_chain: List[EvidenceItem] = Field(default_factory=list)
    consistency_score: float = 0     # 0-100
    summary: str = ""
    analyzed_at: Optional[datetime] = None
    analysis_status: str = "pending"  # pending / analyzing / analyzed / failed
