"""
Worker 主进程 — 从数据库轮询 queued 状态的任务并执行。

启动方式：
    cd backend
    set APP_ROLE=worker
    python -m app.worker.worker

注意：
- API 进程不要启动 Worker（通过 APP_ROLE 环境变量区分）
- Worker 单进程运行，不做多实例并发（避免任务重复执行）
- 任务执行超时默认 600 秒，超时后标记为 failed
"""
import os
import sys
import time
import json
import logging
import signal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.task import AsyncTask
from app.worker.task_registry import get_handler, get_all_task_types
# 导入任务处理模块以触发注册
import app.worker.collector_tasks  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("worker")

# 全局运行标志
_running = True
TASK_TIMEOUT_SECONDS = 600  # 任务超时时间
POLL_INTERVAL = 3  # 轮询间隔（秒）


def signal_handler(signum, frame):
    """优雅退出"""
    global _running
    logger.info(f"收到信号 {signum}，准备退出...")
    _running = False


def claim_next_task(db: Session) -> AsyncTask | None:
    """认领下一个 queued 任务（先到先得，单Worker模式下直接取第一个）"""
    task = db.query(AsyncTask).filter(
        AsyncTask.status == "queued"
    ).order_by(AsyncTask.created_at.asc()).first()

    if task:
        task.status = "running"
        task.started_at = datetime.now()
        task.progress_message = "任务开始执行"
        db.commit()
        db.refresh(task)
        logger.info(f"认领任务 #{task.id} (type={task.task_type})")
    return task


def execute_task(db: Session, task: AsyncTask):
    """执行单个任务"""
    handler = get_handler(task.task_type)
    if not handler:
        raise ValueError(f"未注册的任务类型: {task.task_type}，已注册类型: {get_all_task_types()}")

    result = handler(db, task)
    return result


def complete_task(db: Session, task: AsyncTask, result: dict = None, error: str = None):
    """完成任务（成功或失败）"""
    if error:
        task.status = "failed"
        task.error_message = error[:2000] if error else ""
        task.progress_message = "执行失败"
        logger.error(f"任务 #{task.id} 失败: {error[:200]}")
    else:
        task.status = "succeeded"
        task.progress = 100
        task.progress_message = "执行完成"
        task.result_json = json.dumps(result or {}, ensure_ascii=False)
        logger.info(f"任务 #{task.id} 完成")

    task.finished_at = datetime.now()
    db.commit()


def recover_stuck_tasks(db: Session):
    """恢复卡住的任务（running超过超时时间的标记为failed）"""
    timeout_threshold = datetime.now() - timedelta(seconds=TASK_TIMEOUT_SECONDS)
    stuck_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "running",
        AsyncTask.started_at < timeout_threshold
    ).all()

    for task in stuck_tasks:
        logger.warning(f"任务 #{task.id} 超时（started_at={task.started_at}），标记为failed")
        task.status = "failed"
        task.error_message = f"任务执行超时（>{TASK_TIMEOUT_SECONDS}秒）"
        task.finished_at = datetime.now()
    db.commit()


def run_worker_loop():
    """Worker 主循环（不注册 signal，可在子线程中运行）"""
    global _running
    _running = True

    logger.info("=" * 50)
    logger.info("GEO Worker 启动（内嵌模式）")
    logger.info(f"已注册任务类型: {get_all_task_types()}")
    logger.info(f"轮询间隔: {POLL_INTERVAL}秒 | 任务超时: {TASK_TIMEOUT_SECONDS}秒")
    logger.info("=" * 50)

    while _running:
        try:
            db = SessionLocal()

            # 1. 恢复卡住的任务
            recover_stuck_tasks(db)

            # 2. 认领并执行任务
            task = claim_next_task(db)
            if task:
                try:
                    result = execute_task(db, task)
                    complete_task(db, task, result=result)
                except Exception as e:
                    db.rollback()
                    complete_task(db, task, error=f"{type(e).__name__}: {str(e)}")
            else:
                # 没有任务，等待
                time.sleep(POLL_INTERVAL)

            db.close()

        except Exception as e:
            logger.error(f"Worker 主循环异常: {type(e).__name__}: {e}")
            time.sleep(POLL_INTERVAL)

    logger.info("Worker 已退出")


def stop_worker_loop():
    """停止 Worker 循环（供外部调用）"""
    global _running
    _running = False
    logger.info("收到停止信号，Worker 即将退出...")


def main():
    """Worker 主循环（独立进程模式，注册 signal）"""
    global _running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    run_worker_loop()


if __name__ == "__main__":
    main()
