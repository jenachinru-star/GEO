from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.schemas import *
from app.models import Content
from app.engines import vector_engine

router = APIRouter(prefix="/api/v1/content", tags=["内容资产"])


@router.get("", summary="获取内容列表")
def get_contents(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(Content).filter(Content.user_id == user_id)
    if category:
        query = query.filter(Content.category == category)
    if keyword:
        query = query.filter(Content.title.contains(keyword))
    total = query.count()
    items = query.order_by(Content.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 0, "message": "success", "data": {"total": total, "items": items, "page": page, "page_size": page_size}}


@router.post("", summary="新增内容")
def create_content(data: ContentCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    c = Content(**data.model_dump(), user_id=user_id)
    # 生成向量
    text = f"{c.title} {c.content} {c.summary}"
    vec = vector_engine.text_to_vector(text)
    c.embedding = vector_engine.vector_to_json(vec)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"code": 0, "message": "success", "data": ContentOut.model_validate(c)}


@router.get("/{content_id}", summary="获取内容详情")
def get_content(content_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    c = db.query(Content).filter(Content.id == content_id, Content.user_id == user_id).first()
    if not c:
        return {"code": 404, "message": "内容不存在"}
    return {"code": 0, "message": "success", "data": ContentDetailOut.model_validate(c)}


@router.delete("/{content_id}", summary="删除内容")
def delete_content(content_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    c = db.query(Content).filter(Content.id == content_id, Content.user_id == user_id).first()
    if not c:
        return {"code": 404, "message": "内容不存在"}
    db.delete(c)
    db.commit()
    return {"code": 0, "message": "success"}
