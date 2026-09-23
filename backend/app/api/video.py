"""生视频 API - 基于 Seedance 适配器"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.adapters import adapter_factory

router = APIRouter(prefix="/api/v1/video", tags=["生视频"])


class GenerateVideoRequest(BaseModel):
    prompt: str = Field(..., description="视频描述提示词")
    image_url: Optional[str] = Field(None, description="首帧图片URL（图生视频可选）")
    duration: Optional[int] = Field(5, description="视频时长（秒）")
    resolution: Optional[str] = Field("720p", description="分辨率")


@router.post("/generate", summary="提交视频生成任务")
def generate_video(
    req: GenerateVideoRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """提交视频生成异步任务，返回 task_id"""
    from app.models.video_task import VideoTask
    from app.services.quota_checker import check_quota, QuotaError

    # 配额检查（按月费用上限）
    try:
        check_quota(db, user_id)
    except QuotaError as e:
        raise HTTPException(status_code=402, detail=f"配额不足: {e.message}")

    if not adapter_factory.is_video_configured():
        raise HTTPException(
            status_code=400,
            detail="生视频功能未配置：请在 .env 中设置 SEEDANCE_API_KEY 和 SEEDANCE_BASE_URL"
        )

    video_adapter = adapter_factory.get_video_adapter()
    if not video_adapter:
        raise HTTPException(status_code=400, detail="生视频适配器不可用")

    result = video_adapter.generate_async(
        prompt=req.prompt,
        image_url=req.image_url,
        duration=req.duration,
        resolution=req.resolution,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message or "提交视频任务失败")

    # 入库记录
    task = VideoTask(
        user_id=user_id,
        external_task_id=result.task_id,
        prompt=req.prompt,
        image_url=req.image_url or "",
        duration=req.duration,
        resolution=req.resolution,
        status=result.status or "pending",
    )
    db.add(task)
    db.commit()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": result.task_id,
            "status": result.status,
        }
    }


@router.get("/status/{task_id}", summary="查询视频生成任务状态")
def get_video_status(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """查询视频生成任务状态（校验用户归属）"""
    from app.models.video_task import VideoTask
    from datetime import datetime
    import json

    # 先查本地记录，校验归属
    local_task = db.query(VideoTask).filter(
        VideoTask.external_task_id == task_id,
        VideoTask.user_id == user_id
    ).first()
    if not local_task:
        raise HTTPException(status_code=404, detail="视频任务不存在或不属于当前用户")

    if not adapter_factory.is_video_configured():
        raise HTTPException(status_code=400, detail="生视频功能未配置")

    video_adapter = adapter_factory.get_video_adapter()
    result = video_adapter.get_status(task_id)

    # 更新本地状态
    local_task.status = result.status or local_task.status
    if result.video_urls:
        local_task.video_urls = json.dumps(result.video_urls, ensure_ascii=False)
    if result.error_message:
        local_task.error_message = result.error_message
    if result.status in ("succeeded", "failed") and not local_task.finished_at:
        local_task.finished_at = datetime.utcnow()

    # 任务成功时记录用量（仅记录一次，用 usage_logged 去重）
    if result.status == "succeeded" and not local_task.usage_logged:
        from app.usage_logger import usage_logger
        usage_logger.log(
            platform="seedance",
            model="seedance-1.0",
            prompt_tokens=len(local_task.prompt),
            completion_tokens=0,
            total_tokens=len(local_task.prompt),
            estimated_cost=0.5,  # 生视频每次固定成本0.5元
            user_id=user_id,
            task_type="video_generate",
            ref_id=local_task.id,
            success=True,
            source="http",
        )
        local_task.usage_logged = True

    db.commit()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": task_id,
            "status": result.status,
            "video_urls": result.video_urls,
            "error_message": result.error_message,
        }
    }


@router.get("/config", summary="生视频配置状态")
def get_video_config(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """查询生视频功能配置状态"""
    from app.config import settings
    return {
        "code": 0,
        "message": "success",
        "data": {
            "configured": adapter_factory.is_video_configured(),
            "provider": "seedance" if adapter_factory.is_video_configured() else None,
            "model": settings.SEEDANCE_MODEL or None,
        }
    }
