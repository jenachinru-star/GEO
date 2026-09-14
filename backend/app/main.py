from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import logging

from app.config import settings
from app.database import init_db, SessionLocal
from app.engines.collector import CollectorEngine
from app.models import Question
from app.api import (
    monitor_router,
    content_router,
    knowledge_router,
    competitor_router,
    dashboard_router,
    rag_router,
    system_router,
    export_router,
    auth_router,
    doctor_router,
    semantic_router,
    geo_router,
    article_router,
    entity_router,
    tools_router,
    template_router,
    distribution_router,
)

logger = logging.getLogger(__name__)

# 定时任务调度器
scheduler = BackgroundScheduler()


def scheduled_collect():
    """定时采集任务：每天自动采集所有启用的问题"""
    try:
        logger.info("⏰ 定时采集任务开始执行")
        db = SessionLocal()
        collector = CollectorEngine(db)
        questions = db.query(Question).filter(Question.status == True).all()
        logger.info(f"待采集问题数: {len(questions)}")

        success_count = 0
        for q in questions:
            try:
                records = collector.collect_one_question(q, detect_round=1)
                if any(r.mentioned for r in records):
                    success_count += 1
            except Exception as e:
                logger.error(f"采集问题 [{q.id}] 失败: {e}")

        db.close()
        logger.info(f"✅ 定时采集任务完成，成功提及: {success_count}/{len(questions)}")
    except Exception as e:
        logger.error(f"❌ 定时采集任务异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和定时任务"""
    print(f"🚀 启动 {settings.APP_NAME} v1.0.0")
    print(f"📦 环境: {settings.APP_ENV}")
    print(f"🔧 已启用平台: {settings.get_enabled_platforms()}")
    init_db()
    print("✅ 数据库初始化完成")

    # 启动定时任务（每天上午10点执行采集）
    scheduler.add_job(
        scheduled_collect,
        'cron',
        hour=10,
        minute=0,
        id='daily_collect',
        replace_existing=True
    )
    scheduler.start()
    print("⏰ 定时任务已启动（每天10:00自动采集）")

    yield

    # 关闭时停止调度器
    scheduler.shutdown()
    print("👋 应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="GEO内部智能运营中台 - AI生成式搜索引擎优化监测系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(monitor_router)
app.include_router(content_router)
app.include_router(knowledge_router)
app.include_router(competitor_router)
app.include_router(dashboard_router)
app.include_router(rag_router)
app.include_router(system_router)
app.include_router(export_router)
app.include_router(auth_router)
app.include_router(doctor_router)
app.include_router(semantic_router)
app.include_router(geo_router)
app.include_router(article_router)
app.include_router(entity_router)
app.include_router(tools_router)
app.include_router(template_router)
app.include_router(distribution_router)


@app.get("/", summary="健康检查")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "platforms": settings.get_enabled_platforms()
    }


@app.get("/api/health", summary="API健康检查")
def api_health():
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
