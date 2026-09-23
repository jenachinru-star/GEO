from app.models.platform import Platform
from app.models.question import Question
from app.models.monitor import MonitorRecord
from app.models.content import Content
from app.models.knowledge import Knowledge
from app.models.competitor import Competitor, CompetitorRecord
from app.models.user import User
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.models.article import ArticleDraft
from app.models.subscription import Subscription

# ===== V2 新增模型 =====
from app.models.workspace import Workspace, WorkspaceMember
from app.models.task import AsyncTask
from app.models.content_opportunity import ContentOpportunity

# ===== 数字资产模块 =====
from app.models.asset import (
    AssetSource,
    AssetDocument,
    AssetChunk,
    AssetNote,
    AssetGenerated,
    PubMedCache,
    AssetChatSession,
    AssetChatMessage,
    AssetPublished,
    AssetFolder,
)

# ===== 发布模块 =====
from app.models.publish_account import PublishAccount

# ===== 用量治理模块 =====
from app.models.user_platform_pref import UserPlatformPref
from app.models.user_quota import UserQuota

# ===== 微信公众号数据统计模块 =====
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats

__all__ = [
    "Platform",
    "Question",
    "MonitorRecord",
    "Content",
    "Knowledge",
    "Competitor",
    "CompetitorRecord",
    "User",
    "DoctorProfile",
    "Semantic",
    "ArticleDraft",
    "Subscription",
    "Workspace",
    "WorkspaceMember",
    "AsyncTask",
    "ContentOpportunity",
    # 数字资产模块
    "AssetSource",
    "AssetDocument",
    "AssetChunk",
    "AssetNote",
    "AssetGenerated",
    "PubMedCache",
    "AssetChatSession",
    "AssetChatMessage",
    "AssetPublished",
    "AssetFolder",
    # 发布模块
    "PublishAccount",
    # 用量治理模块
    "UserPlatformPref",
    "UserQuota",
    # 微信公众号数据统计模块
    "WechatAccountStats",
    "WechatArticle",
    "WechatArticleStats",
]
