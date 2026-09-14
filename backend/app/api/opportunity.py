"""内容机会 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.database import get_db
from app.deps import get_current_user_id
from app.models.content_opportunity import ContentOpportunity
from app.models.semantic import Semantic
from app.engines.opportunity_engine import OpportunityEngine

router = APIRouter(prefix="/api/v1/opportunity", tags=["内容机会"])


@router.get("", summary="内容机会列表")
def list_opportunities(
    status: Optional[str] = "open",
    opportunity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 通过 semantic.user_id 过滤（ContentOpportunity 没有直接的 user_id）
    semantics = db.query(Semantic).filter(Semantic.user_id == user_id).all()
    semantic_ids = [s.id for s in semantics]

    query = db.query(ContentOpportunity).filter(ContentOpportunity.question_id.in_(semantic_ids))
    if status:
        query = query.filter(ContentOpportunity.status == status)
    if opportunity_type:
        query = query.filter(ContentOpportunity.opportunity_type == opportunity_type)

    items = query.order_by(ContentOpportunity.priority_score.desc()).all()

    # 关联语义问题文本
    semantic_map = {s.id: s.question for s in semantics}
    result = []
    for opp in items:
        result.append({
            "id": opp.id,
            "question_id": opp.question_id,
            "question_text": semantic_map.get(opp.question_id, ""),
            "opportunity_type": opp.opportunity_type,
            "priority_score": opp.priority_score,
            "evidence": json.loads(opp.evidence_json or "{}"),
            "status": opp.status,
            "created_at": opp.created_at.isoformat() if opp.created_at else None,
        })

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.post("/scan", summary="触发内容机会扫描")
def scan_opportunities(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    engine = OpportunityEngine(db)
    result = engine.scan(user_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/{opp_id}/dismiss", summary="忽略内容机会")
def dismiss_opportunity(
    opp_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    engine = OpportunityEngine(db)
    if engine.dismiss(opp_id, user_id):
        return {"code": 0, "message": "已忽略"}
    raise HTTPException(status_code=404, detail="机会不存在或已处理")
