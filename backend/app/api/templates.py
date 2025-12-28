"""
文书模板相关 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import Response
from typing import Optional, Dict, Any
from app.models import APIResponse, DocTemplate, DocInstance
from app.services import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_template_service(request: Request) -> TemplateService:
    """依赖注入：获取模板服务实例"""
    from app.db import async_db
    if async_db is None:
        raise HTTPException(status_code=503, detail="数据库未连接")
    return TemplateService(async_db)


@router.get("/", response_model=APIResponse)
async def get_templates_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    category: Optional[str] = Query(None, description="模板分类"),
    service: TemplateService = Depends(get_template_service),
):
    """
    获取模板列表
    """
    try:
        result = await service.get_templates_list(
            page=page,
            page_size=page_size,
            category=category,
        )

        return APIResponse(
            success=True,
            data=result["data"],
            pagination=result["pagination"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=APIResponse)
async def get_template_detail(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
):
    """
    获取模板详情
    """
    try:
        template = await service.get_template_detail(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        return APIResponse(success=True, data=template)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=APIResponse)
async def create_template(
    template: DocTemplate,
    service: TemplateService = Depends(get_template_service),
):
    """
    创建模板
    """
    try:
        template_id = await service.create_template(template.dict())

        return APIResponse(success=True, data={"id": template_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=APIResponse)
async def update_template(
    template_id: str,
    template: DocTemplate,
    service: TemplateService = Depends(get_template_service),
):
    """
    更新模板
    """
    try:
        success = await service.update_template(template_id, template.dict())
        if not success:
            raise HTTPException(status_code=404, detail="模板不存在")

        return APIResponse(success=True, data={"updated": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}", response_model=APIResponse)
async def delete_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
):
    """
    删除模板
    """
    try:
        success = await service.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="模板不存在")

        return APIResponse(success=True, data={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/render", response_model=APIResponse)
async def render_template(
    template_id: str,
    field_values: Dict[str, Any],
    service: TemplateService = Depends(get_template_service),
):
    """
    渲染模板（预览）
    """
    try:
        rendered_content = await service.render_template(template_id, field_values)

        return APIResponse(success=True, data={"content": rendered_content})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/export/pdf")
async def export_to_pdf(
    template_id: str,
    field_values: Dict[str, Any],
    service: TemplateService = Depends(get_template_service),
):
    """
    导出为 PDF
    """
    try:
        pdf_bytes = await service.export_to_pdf(template_id, field_values)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={template_id}.pdf"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/export/docx")
async def export_to_docx(
    template_id: str,
    field_values: Dict[str, Any],
    service: TemplateService = Depends(get_template_service),
):
    """
    导出为 DOCX
    """
    try:
        docx_bytes = await service.export_to_docx(template_id, field_values)

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={template_id}.docx"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/categories", response_model=APIResponse)
async def get_template_categories(service: TemplateService = Depends(get_template_service)):
    """
    获取所有模板分类
    """
    try:
        categories = await service.get_categories()
        return APIResponse(success=True, data=categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
