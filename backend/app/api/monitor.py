from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.schemas import *
from app.services import MonitorService
from app.models import Question

router = APIRouter(prefix="/api/v1/monitor", tags=["监测中心"])


@router.get("/questions", summary="获取监测问题列表")
def get_questions(
    category: Optional[str] = None,
    status: Optional[bool] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = MonitorService(db)
    result = service.get_question_list(category, status, keyword, page, page_size)
    return {"code": 0, "message": "success", "data": result}


@router.post("/questions", summary="新增监测问题")
def create_question(data: QuestionCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    q = Question(**data.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"code": 0, "message": "success", "data": QuestionOut.model_validate(q)}


@router.put("/questions/{question_id}", summary="更新监测问题")
def update_question(question_id: int, data: QuestionUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return {"code": 404, "message": "问题不存在"}
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(q, key, value)
    db.commit()
    db.refresh(q)
    return {"code": 0, "message": "success", "data": QuestionOut.model_validate(q)}


@router.delete("/questions/{question_id}", summary="删除监测问题")
def delete_question(question_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return {"code": 404, "message": "问题不存在"}
    db.delete(q)
    db.commit()
    return {"code": 0, "message": "success"}


@router.get("/records", summary="获取监测记录")
def get_records(
    question_id: Optional[int] = None,
    platform_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = MonitorService(db)
    result = service.get_monitor_records(question_id, platform_code, start_date, end_date, page, page_size)
    return {"code": 0, "message": "success", "data": result}


@router.get("/matrix", summary="获取问题×平台矩阵数据")
def get_matrix(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = MonitorService(db)
    result = service.get_question_matrix(date=date)
    return {"code": 0, "message": "success", "data": result}


@router.get("/trend/{question_id}", summary="获取问题趋势")
def get_trend(
    question_id: int,
    platform_code: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = MonitorService(db)
    result = service.get_question_trend(question_id, platform_code, days)
    return {"code": 0, "message": "success", "data": result}


@router.post("/collect", summary="触发采集")
def trigger_collect(data: CollectRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    service = MonitorService(db)
    result = service.trigger_collect(data.question_id)
    return {"code": 0, "message": "success", "data": result}
