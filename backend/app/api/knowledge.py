from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.schemas import *
from app.models import Knowledge
from app.engines import RAGEngine, vector_engine

router = APIRouter(prefix="/api/v1/knowledge", tags=["知识库"])


@router.get("", summary="获取知识库列表")
def get_knowledge(
    category: Optional[str] = None,
    level: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(Knowledge).filter(Knowledge.status == True)
    if category:
        query = query.filter(Knowledge.category == category)
    if level:
        query = query.filter(Knowledge.level == level)
    if keyword:
        query = query.filter(Knowledge.title.contains(keyword))
    total = query.count()
    items = query.order_by(Knowledge.updated_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 0, "message": "success", "data": {"total": total, "items": items, "page": page, "page_size": page_size}}


@router.post("", summary="新增知识库条目")
def create_knowledge(data: KnowledgeCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    k = Knowledge(**data.model_dump())
    # 生成向量
    text = f"{k.title} {k.content}"
    vec = vector_engine.text_to_vector(text)
    k.embedding = vector_engine.vector_to_json(vec)
    db.add(k)
    db.commit()
    db.refresh(k)
    return {"code": 0, "message": "success", "data": KnowledgeOut.model_validate(k)}


@router.put("/{knowledge_id}", summary="更新知识库条目")
def update_knowledge(knowledge_id: int, data: KnowledgeUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    k = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not k:
        return {"code": 404, "message": "知识库条目不存在"}
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(k, key, value)
    k.version += 1
    # 更新向量
    text = f"{k.title} {k.content}"
    vec = vector_engine.text_to_vector(text)
    k.embedding = vector_engine.vector_to_json(vec)
    db.commit()
    db.refresh(k)
    return {"code": 0, "message": "success", "data": KnowledgeOut.model_validate(k)}


@router.delete("/{knowledge_id}", summary="删除知识库条目")
def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    k = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not k:
        return {"code": 404, "message": "知识库条目不存在"}
    k.status = False
    db.commit()
    return {"code": 0, "message": "success"}


@router.post("/search", summary="语义检索知识库")
def search_knowledge(query: str, level: str = "public", top_k: int = 5, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rag = RAGEngine(db)
    results = rag.search_knowledge(query, top_k=top_k, level=level)
    return {"code": 0, "message": "success", "data": [
        {"id": k.id, "title": k.title, "content": k.content, "score": float(score), "category": k.category}
        for k, score in results
    ]}


@router.post("/rebuild-embeddings", summary="重建所有向量")
def rebuild_embeddings(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rag = RAGEngine(db)
    count = rag.rebuild_all_embeddings()
    return {"code": 0, "message": "success", "data": {"updated": count}}
