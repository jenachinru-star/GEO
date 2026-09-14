from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.models.article import ArticleDraft
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.schemas import ArticleCreate, ArticleUpdate, ArticleOut
from app.engines.entity_validator import entity_validator

router = APIRouter(prefix="/api/v1/article", tags=["文章管理"])


@router.get("", summary="获取当前用户的文章列表")
def get_articles(
    semantic_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDraft).filter(ArticleDraft.user_id == user_id)
    if semantic_id:
        query = query.filter(ArticleDraft.semantic_id == semantic_id)
    if status:
        query = query.filter(ArticleDraft.status == status)
    total = query.count()
    items = query.order_by(ArticleDraft.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0, "message": "success",
        "data": {
            "total": total,
            "items": [ArticleOut.model_validate(i).model_dump() for i in items],
            "page": page, "page_size": page_size
        }
    }


@router.post("", summary="创建文章记录")
def create_article(
    data: ArticleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 验证语义属于当前用户
    semantic = db.query(Semantic).filter(
        Semantic.id == data.semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise HTTPException(status_code=404, detail="语义不存在或不属于当前用户")

    article = ArticleDraft(
        user_id=user_id,
        semantic_id=data.semantic_id,
        title=data.title,
        content=data.content,
        platform=data.platform,
        status=data.status
    )
    db.add(article)

    # 更新语义的文章计数
    semantic.article_count = (semantic.article_count or 0) + 1

    # 自动跑实体一致性校验
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if profile:
        result = entity_validator.validate_article(article, profile)
        article.entity_consistent = result.passed

    db.commit()
    db.refresh(article)
    return {"code": 0, "message": "success", "data": ArticleOut.model_validate(article).model_dump()}


@router.get("/{article_id}", summary="获取文章详情")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"code": 0, "message": "success", "data": ArticleOut.model_validate(article).model_dump()}


@router.put("/{article_id}", summary="更新文章")
def update_article(
    article_id: int,
    data: ArticleUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果改了semantic_id，需要更新两个语义的计数
    if "semantic_id" in update_data and update_data["semantic_id"] != article.semantic_id:
        old_semantic = db.query(Semantic).filter(Semantic.id == article.semantic_id).first()
        new_semantic = db.query(Semantic).filter(
            Semantic.id == update_data["semantic_id"], Semantic.user_id == user_id
        ).first()
        if not new_semantic:
            raise HTTPException(status_code=404, detail="目标语义不存在")
        if old_semantic:
            old_semantic.article_count = max(0, (old_semantic.article_count or 0) - 1)
        new_semantic.article_count = (new_semantic.article_count or 0) + 1

    for key, value in update_data.items():
        setattr(article, key, value)

    # 重新跑校验
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if profile:
        result = entity_validator.validate_article(article, profile)
        article.entity_consistent = result.passed

    db.commit()
    db.refresh(article)
    return {"code": 0, "message": "success", "data": ArticleOut.model_validate(article).model_dump()}


@router.delete("/{article_id}", summary="删除文章")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 更新语义计数
    semantic = db.query(Semantic).filter(Semantic.id == article.semantic_id).first()
    if semantic:
        semantic.article_count = max(0, (semantic.article_count or 0) - 1)

    db.delete(article)
    db.commit()
    return {"code": 0, "message": "success"}


@router.post("/{article_id}/validate", summary="重新校验文章实体一致性")
def validate_article(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善医生资料")

    result = entity_validator.validate_article(article, profile)
    article.entity_consistent = result.passed
    db.commit()

    return {"code": 0, "message": "success", "data": result.to_dict()}
