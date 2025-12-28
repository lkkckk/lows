"""
法规相关 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Optional, List
from app.models import APIResponse, SearchRequest, LawCreate
from app.services import LawService
from .auth import verify_admin

router = APIRouter(prefix="/laws", tags=["laws"])


def get_law_service(request: Request) -> LawService:
    """依赖注入：获取法规服务实例"""
    from app.db import async_db
    if async_db is None:
        raise HTTPException(status_code=503, detail="数据库未连接")
    return LawService(async_db)


# ==================== 固定路径路由（必须放在动态路径之前）====================

@router.post("/", response_model=APIResponse)
async def create_law(
    law_in: LawCreate,
    service: LawService = Depends(get_law_service),
):
    """
    手动创建法规
    """
    try:
        result = await service.create_law(law_in)
        return APIResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=APIResponse)
async def get_laws_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    category: Optional[str] = Query(None, description="法规分类"),
    level: Optional[str] = Query(None, description="效力层级"),
    status: Optional[str] = Query(None, description="效力状态"),
    tags: Optional[str] = Query(None, description="标签（逗号分隔）"),
    service: LawService = Depends(get_law_service),
):
    """
    获取法规列表（支持分页和筛选）
    """
    try:
        tags_list = tags.split(",") if tags else None

        result = await service.get_laws_list(
            page=page,
            page_size=page_size,
            category=category,
            level=level,
            status=status,
            tags=tags_list,
        )

        return APIResponse(
            success=True,
            data=result["data"],
            pagination=result["pagination"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=APIResponse)
async def search_global(
    search_request: SearchRequest,
    service: LawService = Depends(get_law_service),
):
    """
    全库搜索（跨法规）
    """
    try:
        result = await service.search_global(
            query=search_request.query,
            page=search_request.page,
            page_size=search_request.page_size,
        )

        return APIResponse(
            success=True,
            data=result["data"],
            pagination=result["pagination"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/categories", response_model=APIResponse)
async def get_categories(service: LawService = Depends(get_law_service)):
    """
    获取所有法规分类
    """
    try:
        categories = await service.get_categories()
        return APIResponse(success=True, data=categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/levels", response_model=APIResponse)
async def get_levels(service: LawService = Depends(get_law_service)):
    """
    获取所有效力层级
    """
    try:
        levels = await service.get_levels()
        return APIResponse(success=True, data=levels)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 动态路径路由（{law_id}）====================

@router.get("/{law_id}", response_model=APIResponse)
async def get_law_detail(
    law_id: str,
    service: LawService = Depends(get_law_service),
):
    """
    获取法规详情
    """
    try:
        law = await service.get_law_detail(law_id)
        if not law:
            raise HTTPException(status_code=404, detail="法规不存在")

        return APIResponse(success=True, data=law)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{law_id}", response_model=APIResponse)
async def update_law(
    law_id: str,
    request: Request,
    service: LawService = Depends(get_law_service),
    _admin: bool = Depends(verify_admin),
):
    """
    更新法规信息（状态、分类等）
    """
    try:
        body = await request.json()
        result = await service.update_law(law_id, body)
        if not result:
            raise HTTPException(status_code=404, detail="法规不存在")
        return APIResponse(success=True, data={"message": "更新成功"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{law_id}", response_model=APIResponse)
async def delete_law(
    law_id: str,
    service: LawService = Depends(get_law_service),
    _admin: bool = Depends(verify_admin),
):
    """
    删除法规及其所有条文
    """
    try:
        result = await service.delete_law(law_id)
        if not result:
            raise HTTPException(status_code=404, detail="法规不存在")
        return APIResponse(success=True, data={"message": "删除成功"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{law_id}/articles", response_model=APIResponse)
async def get_law_articles(
    law_id: str,
    chapter: Optional[str] = Query(None, description="章节筛选"),
    service: LawService = Depends(get_law_service),
):
    """
    获取法规的所有条文
    """
    try:
        articles = await service.get_law_articles(law_id, chapter=chapter)

        return APIResponse(success=True, data=articles)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{law_id}/articles/{article_num}", response_model=APIResponse)
async def get_article_by_number(
    law_id: str,
    article_num: int,
    service: LawService = Depends(get_law_service),
):
    """
    根据条号获取条文
    """
    try:
        article = await service.get_article_by_number(law_id, article_num)
        if not article:
            raise HTTPException(status_code=404, detail="条文不存在")

        return APIResponse(success=True, data=article)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{law_id}/search", response_model=APIResponse)
async def search_in_law(
    law_id: str,
    search_request: SearchRequest,
    service: LawService = Depends(get_law_service),
):
    """
    在单个法规内搜索（支持条号和关键字）
    """
    try:
        result = await service.search_in_law(
            law_id=law_id,
            query=search_request.query,
            page=search_request.page,
            page_size=search_request.page_size,
        )

        return APIResponse(
            success=True,
            data=result["data"],
            pagination=result["pagination"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
