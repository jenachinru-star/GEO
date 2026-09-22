from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.schemas import *
from app.models import Competitor, CompetitorRecord

router = APIRouter(prefix="/api/v1/competitor", tags=["竞品分析"])


@router.get("", summary="获取竞品列表")
def get_competitors(
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(Competitor).filter(Competitor.status == True, Competitor.user_id == user_id)
    if keyword:
        query = query.filter(Competitor.name.contains(keyword))
    items = query.order_by(Competitor.id.desc()).all()
    return {"code": 0, "message": "success", "data": items}


@router.post("", summary="新增竞品")
def create_competitor(data: CompetitorCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    c = Competitor(**data.model_dump(), user_id=user_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"code": 0, "message": "success", "data": CompetitorOut.model_validate(c)}


@router.delete("/{competitor_id}", summary="删除竞品")
def delete_competitor(competitor_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    c = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.user_id == user_id).first()
    if not c:
        return {"code": 404, "message": "竞品不存在"}
    c.status = False
    db.commit()
    return {"code": 0, "message": "success"}


@router.get("/records", summary="获取竞品监测记录")
def get_competitor_records(
    competitor_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(CompetitorRecord)
    if competitor_id:
        query = query.filter(CompetitorRecord.competitor_id == competitor_id)
    if start_date:
        query = query.filter(CompetitorRecord.detect_date >= start_date)
    if end_date:
        query = query.filter(CompetitorRecord.detect_date <= end_date)
    items = query.order_by(CompetitorRecord.detect_time.desc()).limit(200).all()
    return {"code": 0, "message": "success", "data": items}
