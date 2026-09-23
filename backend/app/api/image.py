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


@router.post("/generate", summary="生成图片（异步任务）")
def generate_image(
    req: GenerateImageRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """投递生图异步任务，完成后通过任务接口获取结果"""
    from app.models.task import AsyncTask
    import json

    # 快速失败：未配置时直接返回（不投递任务）
    if not adapter_factory.is_image_configured():
        raise HTTPException(
            status_code=400,
            detail="生图功能未配置：请在 .env 中设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL"
        )

    image_adapter = adapter_factory.get_image_adapter()
    if not image_adapter:
        raise HTTPException(status_code=400, detail="生图适配器不可用")

    # 投递异步任务
    task = AsyncTask(
        task_type="image_generate",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({
            "prompt": req.prompt,
            "width": req.width,
            "height": req.height,
            "n": req.n,
            "style": req.style,
        }, ensure_ascii=False),
        progress_message="等待执行",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "code": 0,
        "message": "生图任务已提交",
        "data": {
            "task_id": task.id,
            "status": "queued",
            "message": "生图中，请在任务中心查看进度",
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
