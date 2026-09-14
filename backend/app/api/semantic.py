"""语义库 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.semantic import Semantic
from app.models.article import ArticleDraft

router = APIRouter(prefix="/api/v1/semantic", tags=["语义库"])


@router.get("", summary="获取当前用户的语义列表")
def get_semantics(
    is_active: bool = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(Semantic).filter(Semantic.user_id == user_id)
    if is_active is not None:
        query = query.filter(Semantic.is_active == is_active)
    semantics = query.order_by(Semantic.id).all()

    result = []
    for s in semantics:
        article_count = db.query(ArticleDraft).filter(
            ArticleDraft.user_id == user_id,
            ArticleDraft.semantic_id == s.id
        ).count()
        result.append({
            "id": s.id,
            "question": s.question,
            "category": s.category,
            "is_active": s.is_active,
            "is_paid": s.is_paid,
            "geo_rate": s.geo_rate,
            "aeo_rate": s.aeo_rate,
            "article_count": article_count,
        })
    return {"code": 0, "message": "success", "data": result}


@router.post("/{semantic_id}/toggle", summary="启用/禁用某个语义")
def toggle_semantic(semantic_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    s = db.query(Semantic).filter(Semantic.id == semantic_id, Semantic.user_id == user_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="语义不存在")
    s.is_active = not s.is_active
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": s.id, "is_active": s.is_active}}


@router.post("/add-paid", summary="付费新增语义（第一阶段仅接口，未做付费校验）")
def add_paid_semantic(
    question: str = Query(..., description="语义问题"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # TODO: 第三阶段接入付费校验
    s = Semantic(user_id=user_id, question=question, category="custom", is_paid=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"code": 0, "message": "success", "data": {"id": s.id, "question": s.question}}
