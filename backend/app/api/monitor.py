from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.database import get_db
from app.deps import get_current_user_id
from app.schemas import *
from app.services import MonitorService
from app.models import Question
from app.models.task import AsyncTask
from app.services.workspace_service import get_user_workspace_id

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
    result = service.get_question_list(category, status, keyword, page, page_size, user_id=user_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/questions", summary="新增监测问题")
def create_question(data: QuestionCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    q = Question(**data.model_dump(), user_id=user_id)
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"code": 0, "message": "success", "data": QuestionOut.model_validate(q)}


@router.put("/questions/{question_id}", summary="更新监测问题")
def update_question(question_id: int, data: QuestionUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    q = db.query(Question).filter(Question.id == question_id, Question.user_id == user_id).first()
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
    q = db.query(Question).filter(Question.id == question_id, Question.user_id == user_id).first()
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
    result = service.get_monitor_records(question_id, platform_code, start_date, end_date, page, page_size, user_id=user_id)
    return {"code": 0, "message": "success", "data": result}


@router.get("/matrix", summary="获取问题×平台矩阵数据")
def get_matrix(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    service = MonitorService(db)
    result = service.get_question_matrix(date=date, user_id=user_id)
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
    result = service.get_question_trend(question_id, platform_code, days, user_id=user_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/collect", summary="触发采集（异步任务，立即返回task_id）")
def trigger_collect(data: CollectRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """触发采集（异步，由Worker执行）"""
    # 获取用户默认 workspace_id
    workspace_id = get_user_workspace_id(db, user_id)

    # 检查是否已有 running 的同类型任务（防止重复提交）
    running_task = db.query(AsyncTask).filter(
        AsyncTask.created_by == user_id,
        AsyncTask.task_type == "monitor_collect",
        AsyncTask.status.in_(["queued", "running"])
    ).first()
    if running_task:
        raise HTTPException(status_code=400, detail=f"已有正在执行的采集任务（ID: {running_task.id}），请等待完成")

    # 创建异步任务
    task = AsyncTask(
        workspace_id=workspace_id,
        task_type="monitor_collect",
        status="queued",
        progress=0,
        progress_message="等待执行",
        payload_json=json.dumps({"question_id": data.question_id, "detect_round": data.detect_round}, ensure_ascii=False),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"code": 0, "message": "任务已创建", "data": {
        "task_id": task.id,
        "status": "queued",
        "message": "采集任务已提交，Worker将在后台执行"
    }}
