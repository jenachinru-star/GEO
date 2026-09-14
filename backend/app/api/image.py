"""生图 API - 基于 Seedream 适配器框架"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.adapters import adapter_factory

router = APIRouter(prefix="/api/v1/image", tags=["生图"])


class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., description="生图提示词")
    width: Optional[int] = Field(1024, description="图片宽度")
    height: Optional[int] = Field(1024, description="图片高度")
    n: Optional[int] = Field(1, description="生成数量")
    style: Optional[str] = Field(None, description="风格参数")


@router.post("/generate", summary="生成图片")
def generate_image(
    req: GenerateImageRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """生成图片（未配置时返回 400）"""
    if not adapter_factory.is_image_configured():
        raise HTTPException(
            status_code=400,
            detail="生图功能未配置：请在 .env 中设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL"
        )

    image_adapter = adapter_factory.get_image_adapter()
    if not image_adapter:
        raise HTTPException(status_code=400, detail="生图适配器不可用")

    result = image_adapter.generate(
        prompt=req.prompt,
        width=req.width,
        height=req.height,
        n=req.n,
        style=req.style,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message or "生图失败")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "image_urls": result.image_urls,
            "task_id": result.task_id,
            "status": result.status,
            "width": result.width,
            "height": result.height,
        }
    }


@router.get("/status", summary="生图配置状态")
def get_image_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """查询生图功能配置状态"""
    from app.config import settings
    return {
        "code": 0,
        "message": "success",
        "data": {
            "configured": adapter_factory.is_image_configured(),
            "provider": "seedream" if adapter_factory.is_image_configured() else None,
            "model": settings.SEEDREAM_MODEL or None,
            "api_key_set": bool(settings.SEEDREAM_API_KEY),
            "base_url_set": bool(settings.SEEDREAM_BASE_URL),
        }
    }
