from app.api.monitor import router as monitor_router
from app.api.content import router as content_router
from app.api.knowledge import router as knowledge_router
from app.api.competitor import router as competitor_router
from app.api.dashboard import router as dashboard_router
from app.api.rag import router as rag_router
from app.api.system import router as system_router
from app.api.export import router as export_router
from app.api.auth import router as auth_router
from app.api.auth_local import router as auth_local_router
from app.api.doctor import router as doctor_router
from app.api.semantic import router as semantic_router
from app.api.geo import router as geo_router
from app.api.article import router as article_router
from app.api.entity import router as entity_router
from app.api.tools import router as tools_router
from app.api.template import router as template_router
from app.api.distribution import router as distribution_router
from app.api.task import router as task_router
from app.api.opportunity import router as opportunity_router
from app.api.image import router as image_router
from app.api.usage import router as usage_router
from app.api.platforms import router as platforms_router
from app.api.upload import router as upload_router

# ===== 数字资产模块 =====
from app.api.asset import router as asset_router
from app.api.asset_summary import router as asset_summary_router
from app.api.asset_search import router as asset_search_router
from app.api.asset_chat import router as asset_chat_router
from app.api.asset_pubmed import router as asset_pubmed_router
from app.api.asset_publish import router as asset_publish_router
from app.api.asset_export import router as asset_export_router
from app.api.asset_folder import router as asset_folder_router
from app.api.asset_tag import router as asset_tag_router

# ===== 新增模块 =====
from app.api.video import router as video_router
from app.api.publish_account import router as publish_account_router

__all__ = [
    "monitor_router",
    "content_router",
    "knowledge_router",
    "competitor_router",
    "dashboard_router",
    "rag_router",
    "system_router",
    "export_router",
    "auth_router",
    "auth_local_router",
    "doctor_router",
    "semantic_router",
    "geo_router",
    "article_router",
    "entity_router",
    "tools_router",
    "template_router",
    "distribution_router",
    "task_router",
    "opportunity_router",
    "image_router",
    "usage_router",
    "platforms_router",
    "upload_router",
    # 数字资产模块
    "asset_router",
    "asset_summary_router",
    "asset_search_router",
    "asset_chat_router",
    "asset_pubmed_router",
    "asset_publish_router",
    "asset_export_router",
    "asset_folder_router",
    "asset_tag_router",
    # 新增模块
    "video_router",
    "publish_account_router",
]

