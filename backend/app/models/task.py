"""异步任务模型 — 所有耗时操作的统一载体（采集/生图/生视频/智能体执行等）"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AsyncTask(Base):
    """异步任务"""
    __tablename__ = "geo_async_task"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=True, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    # geo_refresh / monitor_collect / article_generate / image_generate / video_generate / agent_chat
    status = Column(String(20), default="queued", index=True)
    # queued/running/succeeded/failed/cancelled
    progress = Column(Integer, default=0)  # 0-100
    progress_message = Column(String(500), default="")
    payload_json = Column(Text, default="{}")   # 任务参数（JSON字符串）
    result_json = Column(Text, default="{}")    # 任务结果（JSON字符串）
    error_message = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("geo_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
