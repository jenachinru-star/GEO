"""任务类型 → 处理函数的注册映射"""
from typing import Callable, Dict
from sqlalchemy.orm import Session
from app.models.task import AsyncTask

# 任务处理函数签名：def handler(db: Session, task: AsyncTask) -> dict
TaskHandler = Callable[[Session, AsyncTask], dict]

_task_handlers: Dict[str, TaskHandler] = {}


def register_handler(task_type: str, handler: TaskHandler):
    """注册任务处理函数"""
    _task_handlers[task_type] = handler


def get_handler(task_type: str) -> TaskHandler | None:
    """获取任务处理函数"""
    return _task_handlers.get(task_type)


def get_all_task_types() -> list[str]:
    """获取所有已注册的任务类型"""
    return list(_task_handlers.keys())
