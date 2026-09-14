from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.deps import get_current_user_id
from app.models.distribution import ArticleDistribution
from app.models.article import ArticleDraft

router = APIRouter(prefix="/api/v1/distribution", tags=["文章分发"])


class DistributionCreate(BaseModel):
    article_id: int
    platform: str
    publish_url: str = ""
    status: str = "published"
    note: str = ""


@router.get("", summary="获取分发记录列表")
def get_distributions(
    article_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDistribution).filter(ArticleDistribution.user_id == user_id)
    if article_id:
        query = query.filter(ArticleDistribution.article_id == article_id)
    items = query.order_by(ArticleDistribution.published_at.desc()).all()
    return {"code": 0, "message": "success", "data": {"items": [
        {"id": d.id, "article_id": d.article_id, "platform": d.platform,
         "publish_url": d.publish_url, "status": d.status, "note": d.note,
         "published_at": d.published_at.isoformat() if d.published_at else None}
        for d in items
    ]}}


@router.post("", summary="添加分发记录")
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

    dist = ArticleDistribution(
        user_id=user_id, article_id=data.article_id,
        platform=data.platform, publish_url=data.publish_url,
        status=data.status, note=data.note
    )
    db.add(dist)
    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{dist_id}", summary="删除分发记录")
def delete_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = db.query(ArticleDistribution).filter(
        ArticleDistribution.id == dist_id, ArticleDistribution.user_id == user_id
    ).first()
    if not dist:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(dist)
    db.commit()
    return {"code": 0, "message": "success"}
