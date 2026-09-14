from app.api.monitor import router as monitor_router
from app.api.content import router as content_router
from app.api.knowledge import router as knowledge_router
from app.api.competitor import router as competitor_router
from app.api.dashboard import router as dashboard_router
from app.api.rag import router as rag_router
from app.api.system import router as system_router
from app.api.export import router as export_router
from app.api.auth import router as auth_router
from app.api.doctor import router as doctor_router
from app.api.semantic import router as semantic_router
from app.api.geo import router as geo_router
from app.api.article import router as article_router
from app.api.entity import router as entity_router
from app.api.tools import router as tools_router
from app.api.template import router as template_router
from app.api.distribution import router as distribution_router

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
    "doctor_router",
    "semantic_router",
    "geo_router",
    "article_router",
    "entity_router",
    "tools_router",
    "template_router",
    "distribution_router",
]
