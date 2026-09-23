"""视频生成任务模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from app.database import Base
from datetime import datetime


class VideoTask(Base):
    """视频生成任务记录"""
    __tablename__ = "video_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    external_task_id = Column(String(128), index=True, nullable=False)  # 外部平台任务ID
    prompt = Column(Text, default="")
    image_url = Column(String(512), default="")
    duration = Column(Integer, default=5)
    resolution = Column(String(20), default="720p")
    status = Column(String(20), default="pending")  # pending/running/succeeded/failed
    video_urls = Column(Text, default="[]")  # JSON数组
    error_message = Column(Text, default="")
    platform = Column(String(50), default="seedance")
    usage_logged = Column(Boolean, default=False)  # 是否已记录用量（防止重复）
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
