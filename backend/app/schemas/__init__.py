from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ============ 通用响应 ============
class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


# ============ 平台 ============
class PlatformOut(BaseModel):
    id: int
    code: str
    name: str
    base_url: str
    model: str
    status: bool

    class Config:
        from_attributes = True


# ============ 问题 ============
class QuestionCreate(BaseModel):
    question: str
    category: str = "general"
    tags: str = ""
    priority: int = 5


class QuestionUpdate(BaseModel):
    question: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[bool] = None


class QuestionOut(BaseModel):
    id: int
    question: str
    category: str
    tags: str
    priority: int
    status: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 监测记录 ============
class MonitorRecordOut(BaseModel):
    id: int
    question_id: int
    platform_code: str
    rank: int
    mentioned: bool
    sentiment: float
    raw_answer: str
    detect_date: str
    detect_round: int
    detect_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class MonitorSummary(BaseModel):
    question_id: int
    question: str
    category: str
    platform_stats: dict  # {platform_code: {mention_rate, avg_rank, top1_rate}}
    overall_mention_rate: float
    overall_avg_rank: float


# ============ 内容 ============
class ContentCreate(BaseModel):
    title: str
    category: str = "article"
    tags: str = ""
    content: str = ""
    summary: str = ""
    publish_url: str = ""
    publish_site: str = ""


class ContentOut(BaseModel):
    id: int
    title: str
    category: str
    tags: str
    summary: str
    publish_url: str
    publish_site: str
    citation_count: int
    effect_score: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContentDetailOut(ContentOut):
    content: str


# ============ 竞品 ============
class CompetitorCreate(BaseModel):
    name: str
    aliases: str = ""
    industry: str = ""
    website: str = ""
    description: str = ""


class CompetitorOut(BaseModel):
    id: int
    name: str
    aliases: str
    industry: str
    website: str
    description: str
    status: bool

    class Config:
        from_attributes = True


# ============ 仪表盘 ============
class DashboardStats(BaseModel):
    total_questions: int
    enabled_questions: int
    total_platforms: int
    today_records: int
    overall_mention_rate: float
    overall_top1_rate: float
    avg_rank: float
    abnormal_count: int
    trend_7days: List[dict]
    platform_stats: List[dict]
    top_ranking: List[dict]
    bottom_ranking: List[dict]


# ============ 采集任务 ============
class CollectRequest(BaseModel):
    question_id: Optional[int] = None  # None=全量采集
    detect_round: int = 1


class CollectResult(BaseModel):
    total: int
    success: int
    records_count: int
    platforms: List[str]


# ============ 文章草稿 ============
class ArticleCreate(BaseModel):
    semantic_id: int
    title: str = ""
    content: str = ""
    platform: str = ""  # 发布平台：wechat/xiaohongshu/zhihu/video/douyin/other
    status: str = "draft"  # draft/published


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    platform: Optional[str] = None
    status: Optional[str] = None
    semantic_id: Optional[int] = None


class ArticleOut(BaseModel):
    id: int
    user_id: int
    semantic_id: int
    title: str
    content: str
    platform: str
    status: str
    entity_consistent: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
