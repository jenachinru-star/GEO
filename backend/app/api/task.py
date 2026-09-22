"""异步任务查询 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
from datetime import datetime
from app.database import get_db
from app.deps import get_current_user_id
from app.models.task import AsyncTask

router = APIRouter(prefix="/api/v1/task", tags=["异步任务"])


@router.get("/{task_id}", summary="查询单个任务状态")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    task = db.query(AsyncTask).filter(
        AsyncTask.id == task_id,
        AsyncTask.created_by == user_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 解析 result_json
    result_data = {}
    if task.result_json:
        try:
            result_data = json.loads(task.result_json)
        except:
            pass

    return {"code": 0, "message": "success", "data": {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "result": result_data,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }}


@router.get("", summary="任务列表")
def list_tasks(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(AsyncTask).filter(AsyncTask.created_by == user_id)
    if task_type:
        query = query.filter(AsyncTask.task_type == task_type)
    if status:
        query = query.filter(AsyncTask.status == status)

    total = query.count()
    items = query.order_by(AsyncTask.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()

    return {"code": 0, "message": "success", "data": {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": t.id,
            "task_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "progress_message": t.progress_message,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        } for t in items]
    }}


@router.post("/{task_id}/cancel", summary="取消任务（queued直接取消，running标记取消中由执行线程终止）")
def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    task = db.query(AsyncTask).filter(
        AsyncTask.id == task_id,
        AsyncTask.created_by == user_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"仅 queued/running 状态的任务可取消，当前状态: {task.status}")

    if task.status == "queued":
        # 还未开始执行，直接标记为终态cancelled
        task.status = "cancelled"
        task.finished_at = task.finished_at or datetime.now()
        task.progress_message = "用户取消"
        db.commit()
        return {"code": 0, "message": "任务已取消"}
    else:
        # 正在执行，标记为cancelling，由执行线程在下次进度回调时感知并终止
        task.status = "cancelling"
        task.progress_message = "用户取消中，正在停止..."
        task.error_message = "用户主动取消任务"
        db.commit()
        return {"code": 0, "message": "任务正在取消，执行线程将在当前步骤完成后停止"}
