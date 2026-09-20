from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os
import threading

from app.config import settings

APP_ROLE = os.getenv("APP_ROLE", "api")  # api / worker
AUTO_START_WORKER = os.getenv("AUTO_START_WORKER", "true").lower() == "true"  # API模式下是否自动启动内嵌Worker
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
    task_router,
    opportunity_router,
    image_router,
    auth_local_router,
    usage_router,
    platforms_router,
    upload_router,
    asset_router,
    asset_summary_router,
    asset_search_router,
    video_router,
    publish_account_router,
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
    print(f"🚀 启动 {settings.APP_NAME} v1.0.0 (role={APP_ROLE})")
    print(f"📦 环境: {settings.APP_ENV}")
    print(f"🔧 已启用平台: {settings.get_enabled_platforms()}")
    init_db()
    print("✅ 数据库初始化完成")

    # 启动 LLM 用量日志记录器
    from app.usage_logger import usage_logger
    usage_logger.start()
    print("📊 LLM 用量日志记录器已启动")

    worker_thread = None

    if APP_ROLE == "api":
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

        # 自动启动内嵌 Worker 线程（开发/小型部署用，生产环境可设 AUTO_START_WORKER=false 单独部署Worker）
        if AUTO_START_WORKER:
            from app.worker.worker import run_worker_loop
            worker_thread = threading.Thread(target=run_worker_loop, daemon=True, name="geo-worker")
            worker_thread.start()
            print("🔄 内嵌 Worker 线程已启动（自动执行异步任务）")
        else:
            print("⏭️  AUTO_START_WORKER=false，不启动内嵌Worker（需单独启动Worker进程）")
    else:
        print("⏭️  Worker 模式，不启动定时任务和HTTP服务")

    yield

    # 关闭时停止调度器和Worker
    if APP_ROLE == "api":
        scheduler.shutdown()
        if AUTO_START_WORKER and worker_thread:
            from app.worker.worker import stop_worker_loop
            stop_worker_loop()
            worker_thread.join(timeout=5)
            print("🔄 内嵌 Worker 线程已停止")
    # 停止 LLM 用量日志记录器
    from app.usage_logger import usage_logger
    usage_logger.stop()
    print("📊 LLM 用量日志记录器已停止")
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
app.include_router(task_router)
app.include_router(opportunity_router)
app.include_router(image_router)
app.include_router(auth_local_router)
app.include_router(usage_router)
app.include_router(platforms_router)
app.include_router(upload_router)

# 挂载静态文件服务（上传的文件通过 /uploads/ 访问）
from app.api.upload import mount_static_files
mount_static_files(app)

# 数字资产模块路由
app.include_router(asset_router)
app.include_router(asset_summary_router)
app.include_router(asset_search_router)

# 新增模块路由
app.include_router(video_router)
app.include_router(publish_account_router)


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


def run_worker():
    """以 Worker 角色启动"""
    from app.worker.worker import main as worker_main
    worker_main()


if __name__ == "__main__":
    if APP_ROLE == "worker":
        run_worker()
    else:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG
        )

