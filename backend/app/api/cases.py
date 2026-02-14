"""
案件 + 笔录 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request, BackgroundTasks, UploadFile, File, Form
from typing import Optional, List
from app.models import APIResponse, PaginationInfo, CaseCreate, CaseUpdate, TranscriptCreate
from app.services.case_service import CaseService
from app.services.transcript_service import TranscriptService
from .auth import verify_admin

router = APIRouter(prefix="/cases", tags=["cases"])


def get_case_service(request: Request) -> CaseService:
    """依赖注入：获取案件服务实例"""
    from app.db import async_db
    if async_db is None:
        raise HTTPException(status_code=503, detail="数据库未连接")
    return CaseService(async_db)


def get_transcript_service(request: Request) -> TranscriptService:
    """依赖注入：获取笔录服务实例"""
    from app.db import async_db
    if async_db is None:
        raise HTTPException(status_code=503, detail="数据库未连接")
    return TranscriptService(async_db)


# ==================== 案件管理 ====================

@router.post("/", response_model=APIResponse)
async def create_case(
    case_in: CaseCreate,
    service: CaseService = Depends(get_case_service),
):
    """创建案件"""
    try:
        result = await service.create_case(case_in.model_dump())
        return APIResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=APIResponse)
async def get_cases_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="案件状态: active/archived"),
    case_type: Optional[str] = Query(None, description="案件类型"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    service: CaseService = Depends(get_case_service),
):
    """获取案件列表"""
    try:
        result = await service.get_case_list(
            page=page,
            page_size=page_size,
            status=status,
            case_type=case_type,
            keyword=keyword,
        )
        return APIResponse(
            success=True,
            data=result["items"],
            pagination=PaginationInfo(
                total=result["total"],
                page=result["page"],
                page_size=result["page_size"],
                total_pages=result["total_pages"],
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-transcripts", response_model=APIResponse)
async def search_transcripts_global(
    keyword: str = Query(..., description="搜索关键词"),
    transcript_type: Optional[str] = Query(None, description="笔录类型"),
    subject_role: Optional[str] = Query(None, description="被询问人角色"),
    case_type: Optional[str] = Query(None, description="案件类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TranscriptService = Depends(get_transcript_service),
):
    """全局搜索笔录知识库（跨案件）"""
    try:
        result = await service.search_transcripts(
            keyword=keyword,
            transcript_type=transcript_type,
            subject_role=subject_role,
            case_type=case_type,
            page=page,
            page_size=page_size,
        )
        return APIResponse(
            success=True,
            data=result["items"],
            pagination=PaginationInfo(
                total=result["total"],
                page=result["page"],
                page_size=result["page_size"],
                total_pages=result["total_pages"],
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}", response_model=APIResponse)
async def get_case_detail(
    case_id: str,
    service: CaseService = Depends(get_case_service),
):
    """获取案件详情（含笔录摘要列表）"""
    try:
        result = await service.get_case_detail(case_id)
        if not result:
            raise HTTPException(status_code=404, detail="案件不存在")
        return APIResponse(success=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{case_id}", response_model=APIResponse)
async def update_case(
    case_id: str,
    case_in: CaseUpdate,
    service: CaseService = Depends(get_case_service),
):
    """更新案件信息"""
    try:
        ok = await service.update_case(case_id, case_in.model_dump(exclude_none=True))
        if not ok:
            raise HTTPException(status_code=404, detail="案件不存在")
        return APIResponse(success=True, data={"case_id": case_id})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{case_id}/archive", response_model=APIResponse)
async def archive_case(
    case_id: str,
    archive: bool = Query(True, description="true=归档, false=取消归档"),
    service: CaseService = Depends(get_case_service),
):
    """归档/取消归档案件"""
    try:
        ok = await service.archive_case(case_id, archive)
        if not ok:
            raise HTTPException(status_code=404, detail="案件不存在")
        return APIResponse(success=True, data={"case_id": case_id, "status": "archived" if archive else "active"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{case_id}", response_model=APIResponse)
async def delete_case(
    case_id: str,
    service: CaseService = Depends(get_case_service),
):
    """删除案件（连带删除所有笔录）"""
    try:
        ok = await service.delete_case(case_id)
        if not ok:
            raise HTTPException(status_code=404, detail="案件不存在")
        return APIResponse(success=True, data={"deleted": case_id})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 笔录管理 ====================

@router.post("/{case_id}/transcripts", response_model=APIResponse)
async def create_transcript(
    case_id: str,
    transcript_in: TranscriptCreate,
    background_tasks: BackgroundTasks,
    service: TranscriptService = Depends(get_transcript_service),
):
    """添加笔录（文本方式）"""
    try:
        result = await service.create_transcript(case_id, transcript_in.model_dump())
        # 自动触发 AI 分析
        if transcript_in.auto_analyze:
            background_tasks.add_task(
                service.analyze_transcript,
                case_id,
                result["transcript_id"],
            )
        return APIResponse(success=True, data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{case_id}/transcripts/upload", response_model=APIResponse)
async def upload_transcript(
    case_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    type: str = Form(...),
    subject_name: str = Form(...),
    subject_role: str = Form(...),
    auto_analyze: bool = Form(True),
    service: TranscriptService = Depends(get_transcript_service),
):
    """上传笔录文件（.docx / .txt）"""
    # 校验文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("doc", "docx", "txt"):
        raise HTTPException(status_code=400, detail="仅支持 .doc、.docx 和 .txt 文件")

    # 校验大小（10MB）
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    try:
        # 解析文件内容
        if ext == "docx":
            content = TranscriptService.parse_docx(file_bytes)
        elif ext == "doc":
            content = TranscriptService.parse_doc(file_bytes)
        else:
            content = TranscriptService.parse_txt(file_bytes)

        data = {
            "title": title,
            "type": type,
            "subject_name": subject_name,
            "subject_role": subject_role,
            "content": content,
            "file_name": file.filename,
        }
        result = await service.create_transcript(case_id, data)

        if auto_analyze:
            background_tasks.add_task(
                service.analyze_transcript,
                case_id,
                result["transcript_id"],
            )
        return APIResponse(success=True, data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/transcripts", response_model=APIResponse)
async def get_transcript_list(
    case_id: str,
    service: TranscriptService = Depends(get_transcript_service),
):
    """获取案件下所有笔录列表"""
    try:
        items = await service.get_transcript_list(case_id)
        return APIResponse(success=True, data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/transcripts/{transcript_id}", response_model=APIResponse)
async def get_transcript_detail(
    case_id: str,
    transcript_id: str,
    service: TranscriptService = Depends(get_transcript_service),
):
    """获取笔录详情（含分析结果）"""
    try:
        result = await service.get_transcript_detail(case_id, transcript_id)
        if not result:
            raise HTTPException(status_code=404, detail="笔录不存在")
        return APIResponse(success=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{case_id}/transcripts/{transcript_id}", response_model=APIResponse)
async def delete_transcript(
    case_id: str,
    transcript_id: str,
    service: TranscriptService = Depends(get_transcript_service),
):
    """删除笔录"""
    try:
        ok = await service.delete_transcript(case_id, transcript_id)
        if not ok:
            raise HTTPException(status_code=404, detail="笔录不存在")
        return APIResponse(success=True, data={"deleted": transcript_id})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{case_id}/transcripts/{transcript_id}/analyze", response_model=APIResponse)
async def trigger_analysis(
    case_id: str,
    transcript_id: str,
    background_tasks: BackgroundTasks,
    service: TranscriptService = Depends(get_transcript_service),
):
    """触发/重新触发 AI 分析"""
    try:
        # 检查笔录是否存在
        status = await service.get_analysis_status(case_id, transcript_id)
        if status is None:
            raise HTTPException(status_code=404, detail="笔录不存在")
        background_tasks.add_task(
            service.analyze_transcript, case_id, transcript_id
        )
        return APIResponse(success=True, data={
            "transcript_id": transcript_id,
            "analysis_status": "analyzing",
            "message": "分析任务已提交",
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/transcripts/{transcript_id}/status", response_model=APIResponse)
async def get_analysis_status(
    case_id: str,
    transcript_id: str,
    service: TranscriptService = Depends(get_transcript_service),
):
    """查询分析状态"""
    try:
        status = await service.get_analysis_status(case_id, transcript_id)
        if status is None:
            raise HTTPException(status_code=404, detail="笔录不存在")
        return APIResponse(success=True, data={"analysis_status": status})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 交叉分析（二期） ====================

@router.post("/{case_id}/cross-analyze", response_model=APIResponse)
async def trigger_cross_analysis(
    case_id: str,
    background_tasks: BackgroundTasks,
    service: TranscriptService = Depends(get_transcript_service),
    case_service: CaseService = Depends(get_case_service),
):
    """触发交叉分析（需 ≥2 份已分析笔录）"""
    try:
        # 检查案件是否存在
        case = await case_service.get_case_detail(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="案件不存在")

        # 检查已分析笔录数量
        transcripts = case.get("transcripts", [])
        analyzed_count = sum(1 for t in transcripts if t.get("analysis_status") == "analyzed")
        if analyzed_count < 2:
            raise HTTPException(
                status_code=400,
                detail=f"至少需要 2 份已分析的笔录，当前已分析 {analyzed_count} 份"
            )

        # 异步触发交叉分析
        background_tasks.add_task(service.cross_analyze, case_id)

        return APIResponse(success=True, data={
            "case_id": case_id,
            "analysis_status": "analyzing",
            "analyzed_transcripts": analyzed_count,
            "message": "交叉分析任务已提交",
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/cross-analysis", response_model=APIResponse)
async def get_cross_analysis(
    case_id: str,
    service: TranscriptService = Depends(get_transcript_service),
):
    """获取交叉分析结果"""
    try:
        result = await service.get_cross_analysis_status(case_id)
        if result is None:
            raise HTTPException(status_code=404, detail="案件不存在")
        return APIResponse(success=True, data=result if result else {"analysis_status": "not_started"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
