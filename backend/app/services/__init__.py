"""
服务包初始化
"""
from .law_service import LawService
from .template_service import TemplateService
from .case_service import CaseService
from .transcript_service import TranscriptService

__all__ = ["LawService", "TemplateService", "CaseService", "TranscriptService"]
