"""语义库 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.deps import get_current_user_id
from app.models.semantic import Semantic
from app.models.article import ArticleDraft
from app.models.doctor import DoctorProfile
from app.engines.semantic_extender import SemanticExtender

router = APIRouter(prefix="/api/v1/semantic", tags=["语义库"])


class ExtendSaveRequest(BaseModel):
    """批量保存延伸问题的请求体"""
    questions: List[str]
    parent_id: int
    extend_type: str  # synonym / deep


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


@router.post("/{semantic_id}/extend", summary="生成语义延伸预览（同义变体+深度延伸，不直接保存）")
def extend_semantic(
    semantic_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    s = db.query(Semantic).filter(Semantic.id == semantic_id, Semantic.user_id == user_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="语义不存在")

    # 获取医生资料（用于深度延伸）
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    profile_dict = {}
    if profile:
        profile_dict = {
            "real_name": profile.real_name,
            "hospital": profile.hospital,
            "department": profile.department,
            "specialty": profile.specialty,
            "city": profile.city,
        }

    # 获取现有问题列表（用于去重）
    existing = [q.question for q in db.query(Semantic).filter(Semantic.user_id == user_id).all()]

    extender = SemanticExtender(db=db, user_id=user_id)
    result = extender.extend(s.question, profile_dict, existing)

    return {"code": 0, "message": "success", "data": result}


@router.post("/extend-batch", summary="批量生成语义延伸预览（对所有启用的语义）")
def extend_batch(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    semantics = db.query(Semantic).filter(
        Semantic.user_id == user_id,
        Semantic.is_active == True,
        Semantic.parent_id.is_(None)  # 只对原始问题延伸，不对延伸结果再延伸
    ).all()

    if not semantics:
        return {"code": 0, "message": "success", "data": {"results": [], "count": 0}}

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    profile_dict = {}
    if profile:
        profile_dict = {
            "real_name": profile.real_name,
            "hospital": profile.hospital,
            "department": profile.department,
            "specialty": profile.specialty,
            "city": profile.city,
        }

    existing = [q.question for q in db.query(Semantic).filter(Semantic.user_id == user_id).all()]

    extender = SemanticExtender(db=db, user_id=user_id)
    questions = [s.question for s in semantics]
    results = extender.extend_batch(questions, profile_dict, existing)

    return {"code": 0, "message": "success", "data": {"results": results, "count": len(results)}}


@router.post("/extend/save", summary="批量保存勾选的延伸问题")
def save_extended(
    req: ExtendSaveRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 验证 parent_id 属于当前用户
    parent = db.query(Semantic).filter(Semantic.id == req.parent_id, Semantic.user_id == user_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="父语义不存在")

    if req.extend_type not in ("synonym", "deep"):
        raise HTTPException(status_code=400, detail="extend_type 必须是 synonym 或 deep")

    saved = []
    for question in req.questions:
        # 确保以问号结尾
        if not question.endswith('？') and not question.endswith('?'):
            question = question + '？'
        # 检查重复
        exists = db.query(Semantic).filter(
            Semantic.user_id == user_id,
            Semantic.question == question
        ).first()
        if exists:
            continue
        s = Semantic(
            user_id=user_id,
            question=question,
            category="extended",
            is_active=True,
            parent_id=req.parent_id,
            extend_type=req.extend_type
        )
        db.add(s)
        saved.append(s)

    db.commit()
    for s in saved:
        db.refresh(s)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "saved_count": len(saved),
            "saved": [{"id": s.id, "question": s.question} for s in saved]
        }
    }
