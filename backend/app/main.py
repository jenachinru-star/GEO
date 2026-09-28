from fastapi import FastAPI, Request
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
from app.api import (
    monitor_router,
    content_router,
    competitor_router,
    dashboard_router,
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
    asset_publish_router,
    asset_chat_router,
    asset_export_router,
    asset_folder_router,
    asset_pubmed_router,
    asset_tag_router,
    video_router,
    publish_account_router,
    benchmark_router,
    audit_router,
)
from app.api.usage_governance import router as usage_governance_router

logger = logging.getLogger(__name__)

# 定时任务调度器
scheduler = BackgroundScheduler()


def scheduled_collect():
    """定时采集任务：每天自动为所有有启用语义的用户投递采集任务"""
    try:
        import json
        from app.models.task import AsyncTask
        from app.models.semantic import Semantic
        from app.models.doctor import DoctorProfile

        logger.info("⏰ 定时采集任务开始执行")
        db = SessionLocal()

        # 查找所有有启用语义的用户（项目已迁移到Semantic表）
        user_ids = [
            row[0] for row in
            db.query(Semantic.user_id).filter(
                Semantic.is_active == True,
                Semantic.user_id.isnot(None)
            ).distinct().all()
        ]
        logger.info(f"待采集用户数: {len(user_ids)}")

        task_count = 0
        for user_id in user_ids:
            try:
                # 检查用户是否有医生资料
                profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
                if not profile:
                    logger.warning(f"用户 [{user_id}] 无医生资料，跳过定时采集")
                    continue

                # 检查是否已有running/queued的采集任务，避免重复投递
                existing = db.query(AsyncTask).filter(
                    AsyncTask.created_by == user_id,
                    AsyncTask.task_type == "geo_refresh",
                    AsyncTask.status.in_(["queued", "running"])
                ).first()
                if existing:
                    logger.info(f"用户 [{user_id}] 已有进行中的采集任务 #{existing.id}，跳过")
                    continue

                # 投递采集任务（由Worker执行，自动受益于用户平台过滤和并发采集）
                task = AsyncTask(
                    task_type="geo_refresh",
                    status="queued",
                    created_by=user_id,
                    payload_json=json.dumps({"user_id": user_id}, ensure_ascii=False),
                    progress_message="定时采集，等待执行",
                )
                db.add(task)
                db.commit()
                task_count += 1
                logger.info(f"用户 [{user_id}] 定时采集任务已投递 #{task.id}")
            except Exception as e:
                logger.error(f"为用户 [{user_id}] 投递定时采集任务失败: {e}")
                db.rollback()

        db.close()
        logger.info(f"✅ 定时采集任务完成，共投递 {task_count} 个采集任务")
    except Exception as e:
        logger.error(f"❌ 定时采集任务异常: {e}")


def scheduled_collect_wechat_data():
    """定时采集微信公众号数据：每天凌晨2点，重查"昨天/3天前/7天前"三个群发日。
    getarticletotal 按群发日返回该文章截至调用日的累计行（最多7天），
    重查三个群发日即可逐步填满 day_1/3/7 快照，并自动回填遗漏。
    """
    try:
        import json
        from datetime import date, timedelta
        from app.models.publish_account import PublishAccount
        from app.models.task import AsyncTask

        logger.info("⏰ 微信公众号数据定时采集开始")
        db = SessionLocal()

        # 查找所有已验证的微信公众号账号
        accounts = db.query(PublishAccount).filter(
            PublishAccount.platform == "wechat",
            PublishAccount.login_status == "valid",
            PublishAccount.app_id != "",
        ).all()

        # 三个重查群发日：昨天 / 3天前 / 7天前
        yesterday = date.today() - timedelta(days=1)
        ref_dates = [
            yesterday.isoformat(),
            (yesterday - timedelta(days=2)).isoformat(),  # 3天前
            (yesterday - timedelta(days=6)).isoformat(),  # 7天前
        ]

        task_count = 0
        for account in accounts:
            try:
                # 检查是否已有running/queued的采集任务，避免重复投递
                existing = db.query(AsyncTask).filter(
                    AsyncTask.task_type == "wechat_data_collect",
                    AsyncTask.status.in_(["queued", "running"]),
                    AsyncTask.created_by == account.user_id,
                ).first()
                if existing:
                    logger.info(f"账号 [{account.account_name}] 已有采集任务在执行，跳过")
                    continue

                task = AsyncTask(
                    task_type="wechat_data_collect",
                    status="queued",
                    created_by=account.user_id,
                    payload_json=json.dumps(
                        {"account_id": account.id, "dates": ref_dates},
                        ensure_ascii=False),
                    progress_message=f"定时采集微信公众号数据 [{account.account_name}]（3个群发日）",
                )
                db.add(task)
                db.commit()
                task_count += 1
                logger.info(f"账号 [{account.account_name}] 数据采集任务已投递 #{task.id}")
            except Exception as e:
                logger.error(f"为账号 [{account.account_name}] 投递采集任务失败: {e}")
                db.rollback()

        db.close()
        logger.info(f"✅ 微信公众号数据定时采集完成，共投递 {task_count} 个任务")
    except Exception as e:
        logger.error(f"❌ 微信公众号数据定时采集异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和定时任务"""
    print(f"🚀 启动 {settings.APP_NAME} v1.0.0 (role={APP_ROLE})")
    print(f"📦 环境: {settings.APP_ENV}")
    print(f"🔧 已启用平台: {settings.get_enabled_platforms()}")
    init_db()
    print("✅ 数据库初始化完成")

    # 从Platform表加载平台配置（数据库优先，.env兜底）
    from app.adapters import adapter_factory
    db = SessionLocal()
    try:
        adapter_factory.load_from_db(db)
    finally:
        db.close()

    # 启动 LLM 用量日志记录器
    from app.usage_logger import usage_logger
    usage_logger.start()
    print("📊 LLM 用量日志记录器已启动")

    worker_threads = []

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

        # 微信公众号数据定时采集（每天凌晨2点）
        scheduler.add_job(
            scheduled_collect_wechat_data,
            'cron',
            hour=2,
            minute=0,
            id='daily_wechat_data_collect',
            replace_existing=True
        )

        scheduler.start()
        print("⏰ 定时任务已启动（每天10:00自动采集）")
        print("⏰ 微信公众号数据定时采集已启动（每天02:00自动采集）")

        # 自动启动内嵌 Worker 线程（2个并发工作线程，开发/小型部署用）
        if AUTO_START_WORKER:
            from app.worker.worker import run_worker_loop
            for i in range(2):
                t = threading.Thread(target=run_worker_loop, daemon=True, name=f"geo-worker-{i}")
                t.start()
                worker_threads.append(t)
            print("🔄 内嵌 Worker 已启动（2个并发工作线程）")
        else:
            print("⏭️  AUTO_START_WORKER=false，不启动内嵌Worker（需单独启动Worker进程）")
    else:
        print("⏭️  Worker 模式，不启动定时任务和HTTP服务")

    yield

    # 关闭时停止调度器和Worker
    if APP_ROLE == "api":
        scheduler.shutdown()
        if AUTO_START_WORKER and worker_threads:
            from app.worker.worker import stop_worker_loop
            stop_worker_loop()
            for t in worker_threads:
                t.join(timeout=5)
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
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
)

# CORS配置 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API速率限制中间件（每IP每分钟120次请求）
from app.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

# 阶段四C：审计日志中间件（先添加，在内层）
from app.middleware.audit_middleware import AuditMiddleware
app.add_middleware(AuditMiddleware)

# 阶段四C：全局错误处理中间件（后添加，在外层，最先捕获异常）
from app.middleware.error_handler import ErrorHandlerMiddleware
app.add_middleware(ErrorHandlerMiddleware)


# usage_context中间件：HTTP请求自动设置user_id，使LLM调用能进行配额检查
@app.middleware("http")
async def usage_context_middleware(request: Request, call_next):
    from app.services.iam_service import IAMService
    from app.usage_context import usage_context
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = IAMService.verify_jwt(auth_header[7:])
            user_id = payload.get("user_id") if payload else None
        except Exception:
            pass
    ctx_token = usage_context.set(user_id=user_id, task_type="http_request", ref_id=None) if user_id else None
    try:
        response = await call_next(request)
        return response
    finally:
        if ctx_token:
            usage_context.reset(ctx_token)

# 注册路由
app.include_router(monitor_router)
app.include_router(content_router)
app.include_router(competitor_router)
app.include_router(dashboard_router)
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
app.include_router(asset_publish_router)
app.include_router(asset_chat_router)
app.include_router(asset_export_router)
app.include_router(asset_folder_router)
app.include_router(asset_pubmed_router)
app.include_router(asset_tag_router)

# 新增模块路由
app.include_router(video_router)
app.include_router(publish_account_router)
app.include_router(usage_governance_router)

# 阶段四C路由
app.include_router(benchmark_router)
app.include_router(audit_router)


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
            reload=settings.is_debug
        )





