from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.deps import get_current_user_id
from app.models.distribution import ArticleDistribution
from app.models.article import ArticleDraft
from app.services.distribution_service import DistributionService

router = APIRouter(prefix="/api/v1/distribution", tags=["文章分发"])


class DistributionCreate(BaseModel):
    article_id: int
    platform: str
    publish_url: str = ""
    status: str = "draft"  # 创建时默认 draft
    note: str = ""


class DistributionStatusUpdate(BaseModel):
    status: str  # scheduled / processing / published / failed / removed
    publish_url: str = ""
    note: str = ""


@router.get("", summary="获取分发记录列表")
def get_distributions(
    article_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDistribution).filter(ArticleDistribution.user_id == user_id)
    if article_id:
        query = query.filter(ArticleDistribution.article_id == article_id)
    if status:
        query = query.filter(ArticleDistribution.status == status)
    items = query.order_by(ArticleDistribution.created_at.desc()).all()
    return {"code": 0, "message": "success", "data": {"items": [
        {
            "id": d.id,
            "article_id": d.article_id,
            "platform": d.platform,
            "publish_url": d.publish_url,
            "status": d.status,
            "note": d.note,
            "publish_mode": d.publish_mode,
            "retry_count": d.retry_count,
            "failed_reason": d.failed_reason,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in items
    ]}}


@router.post("", summary="创建分发记录")
def create_distribution(
    data: DistributionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == data.article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 校验状态合法性
    valid_statuses = ["draft", "scheduled", "processing", "published", "failed", "removed"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态: {data.status}，合法值: {valid_statuses}")

    dist = ArticleDistribution(
        user_id=user_id, article_id=data.article_id,
        platform=data.platform, publish_url=data.publish_url,
        status=data.status, note=data.note,
        publish_mode="manual",
    )
    if data.status == "published":
        dist.published_at = datetime.now()
    db.add(dist)
    db.commit()
    db.refresh(dist)
    return {"code": 0, "message": "success", "data": {"id": dist.id}}


@router.patch("/{dist_id}/status", summary="状态流转（计划/开始/成功/失败/重试/移除）")
def update_status(
    dist_id: int,
    data: DistributionStatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    dist = DistributionService.transition(
        db, dist, data.status,
        note=data.note, publish_url=data.publish_url
    )
    return {"code": 0, "message": "success", "data": {"id": dist.id, "status": dist.status}}


@router.post("/{dist_id}/retry", summary="重试发布（failed → processing）")
def retry_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    dist = DistributionService.retry(db, dist)
    return {"code": 0, "message": "success", "data": {"id": dist.id, "status": dist.status, "retry_count": dist.retry_count}}


@router.delete("/{dist_id}", summary="删除分发记录（物理删除，仅 draft 状态允许）")
def delete_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    if dist.status != "draft":
        raise HTTPException(status_code=400, detail=f"仅 draft 状态的记录可以物理删除，当前状态: {dist.status}。请使用移除（removed）接口")
    db.delete(dist)
    db.commit()
    return {"code": 0, "message": "success"}
