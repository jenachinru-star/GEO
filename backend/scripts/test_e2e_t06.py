"""
T06 端到端流程测试脚本
测试：采集异步流程 + Distribution状态机 + 重复提交防护
直接调用API函数和Worker逻辑，绕过HTTP认证层
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.models.task import AsyncTask
from app.models.distribution import ArticleDistribution
from app.models.article import ArticleDraft
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.services.distribution_service import DistributionService
from app.worker.worker import claim_next_task, execute_task, complete_task
from app.worker import collector_tasks  # noqa: F401  触发注册
from fastapi import HTTPException

init_db()
db = SessionLocal()

print("=" * 60)
print("T06 端到端流程测试")
print("=" * 60)

# ===== 测试1: /geo/refresh 创建异步任务 =====
print("\n[测试1] /geo/refresh 创建异步任务")
try:
    from app.api.geo import refresh_data
    # 直接调用函数，传入 db 和 user_id=1
    result = refresh_data(db=db, user_id=1)
    task_id = result["data"]["task_id"]
    status = result["data"]["status"]
    print(f"  返回 task_id={task_id}, status={status}")
    assert task_id is not None
    assert status == "queued"
    print("  PASS: 立即返回 task_id，不阻塞")
except HTTPException as e:
    print(f"  接口返回 HTTPException: {e.status_code} - {e.detail}")
    if e.status_code == 400 and "已有正在执行" in str(e.detail):
        print("  PASS: 重复提交防护生效（已有运行中任务）")
        # 获取已存在的任务ID
        existing = db.query(AsyncTask).filter(
            AsyncTask.created_by == 1,
            AsyncTask.task_type == "geo_refresh",
            AsyncTask.status.in_(["queued", "running"])
        ).first()
        task_id = existing.id if existing else None
    else:
        print(f"  FAIL: 意外的错误: {e}")
        task_id = None
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")
    task_id = None

# ===== 测试2: 重复提交防护 =====
print("\n[测试2] 重复提交防护")
try:
    result = refresh_data(db=db, user_id=1)
    print("  FAIL: 重复提交没有返回400")
except HTTPException as e:
    if e.status_code == 400:
        print(f"  PASS: 重复提交返回 400 - {e.detail}")
    else:
        print(f"  FAIL: 返回了意外的状态码 {e.status_code}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# ===== 测试3: Worker 认领并执行任务 =====
print("\n[测试3] Worker 认领并执行任务")
if task_id:
    # 先确认任务是 queued 状态
    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    print(f"  任务 #{task_id} 当前状态: {task.status}")

    # Worker 认领
    claimed = claim_next_task(db)
    if claimed and claimed.id == task_id:
        print(f"  PASS: Worker 认领任务 #{claimed.id}, 状态={claimed.status}")
        assert claimed.status == "running"

        # 执行任务（可能会失败，因为采集需要AI平台配置，但Worker应该能处理）
        print("  执行任务中...（采集可能需要较长时间或因AI平台配置失败）")
        try:
            result = execute_task(db, claimed)
            complete_task(db, claimed, result=result)
            print(f"  PASS: 任务执行完成，状态={claimed.status}")
        except Exception as e:
            complete_task(db, claimed, error=f"{type(e).__name__}: {e}")
            print(f"  任务执行失败（预期内，可能因AI平台配置）: {type(e).__name__}: {str(e)[:100]}")
            print(f"  任务状态={claimed.status}")

        # 验证最终状态
        db.refresh(claimed)
        final_status = claimed.status
        print(f"  最终状态: {final_status}")
        assert final_status in ["succeeded", "failed"], f"意外的最终状态: {final_status}"
        print("  PASS: Worker 能认领并执行 geo_refresh 任务")
    else:
        print(f"  FAIL: Worker 没有认领任务 #{task_id}，认领了: {claimed.id if claimed else 'None'}")
else:
    print("  SKIP: 没有可测试的任务ID")

# ===== 测试4: 任务查询API =====
print("\n[测试4] 任务查询API")
try:
    from app.api.task import get_task, list_tasks, cancel_task
    # 创建一个测试任务用于查询
    test_task = AsyncTask(
        task_type="monitor_collect",
        status="queued",
        progress=0,
        progress_message="测试任务",
        payload_json=json.dumps({"question_id": None, "detect_round": 1}),
        created_by=1,
    )
    db.add(test_task)
    db.commit()
    db.refresh(test_task)
    test_id = test_task.id

    # 查询单个任务
    result = get_task(task_id=test_id, db=db, user_id=1)
    assert result["data"]["id"] == test_id
    assert result["data"]["task_type"] == "monitor_collect"
    print(f"  PASS: GET /task/{test_id} 返回正确数据")

    # 查询任务列表
    result = list_tasks(page=1, page_size=10, db=db, user_id=1)
    assert result["data"]["total"] >= 2
    print(f"  PASS: GET /task 返回列表，total={result['data']['total']}")

    # 取消 queued 任务
    result = cancel_task(task_id=test_id, db=db, user_id=1)
    db.refresh(test_task)
    assert test_task.status == "cancelled"
    print(f"  PASS: POST /task/{test_id}/cancel 取消成功，状态={test_task.status}")

    # 尝试取消非 queued 任务（应该返回400）
    try:
        cancel_task(task_id=test_id, db=db, user_id=1)
        print("  FAIL: 取消已取消的任务没有返回400")
    except HTTPException as e:
        if e.status_code == 400:
            print(f"  PASS: 取消非queued任务返回400 - {e.detail}")
        else:
            print(f"  FAIL: 意外状态码 {e.status_code}")

except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ===== 测试5: Distribution 状态机 =====
print("\n[测试5] Distribution 状态机流转")
try:
    # 找一篇文章
    article = db.query(ArticleDraft).filter(ArticleDraft.user_id == 1).first()
    if not article:
        # 创建一篇测试文章
        article = ArticleDraft(
            user_id=1,
            title="测试文章",
            content="测试内容",
            status="draft",
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        print(f"  创建测试文章 #{article.id}")

    # 创建一个 draft 状态的分发记录
    dist = ArticleDistribution(
        user_id=1,
        article_id=article.id,
        platform="wechat",
        publish_url="",
        status="draft",
        note="",
        publish_mode="manual",
    )
    db.add(dist)
    db.commit()
    db.refresh(dist)
    print(f"  创建分发记录 #{dist.id}, 状态=draft")

    # draft → scheduled
    dist = DistributionService.transition(db, dist, "scheduled", note="计划发布")
    assert dist.status == "scheduled"
    print(f"  PASS: draft → scheduled, scheduled_at={dist.scheduled_at}")

    # scheduled → processing
    dist = DistributionService.transition(db, dist, "processing", note="开始发布")
    assert dist.status == "processing"
    print(f"  PASS: scheduled → processing, retry_count={dist.retry_count}")

    # processing → published
    dist = DistributionService.transition(db, dist, "published", note="发布成功", publish_url="https://example.com/article")
    assert dist.status == "published"
    print(f"  PASS: processing → published, publish_url={dist.publish_url}")

    # 非法流转: published → processing（应该返回400）
    try:
        DistributionService.transition(db, dist, "processing")
        print("  FAIL: 非法流转 published → processing 没有返回400")
    except HTTPException as e:
        if e.status_code == 400:
            print(f"  PASS: 非法流转 published → processing 返回400")
        else:
            print(f"  FAIL: 意外状态码 {e.status_code}")

    # 测试 failed → retry 流程
    dist2 = ArticleDistribution(
        user_id=1,
        article_id=article.id,
        platform="zhihu",
        status="draft",
        publish_mode="manual",
    )
    db.add(dist2)
    db.commit()
    db.refresh(dist2)
    dist2 = DistributionService.transition(db, dist2, "scheduled")
    dist2 = DistributionService.transition(db, dist2, "processing")
    dist2 = DistributionService.transition(db, dist2, "failed", note="发布失败: 网络错误")
    assert dist2.status == "failed"
    assert dist2.failed_reason == "发布失败: 网络错误"
    print(f"  PASS: processing → failed, failed_reason={dist2.failed_reason}")

    # failed → processing (retry)
    dist2 = DistributionService.retry(db, dist2)
    assert dist2.status == "processing"
    assert dist2.retry_count >= 1
    print(f"  PASS: failed → processing (retry), retry_count={dist2.retry_count}")

    print("  PASS: Distribution 状态机全部流转测试通过")

except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ===== 测试6: 分析器bug修复验证 =====
print("\n[测试6] 分析器bug修复验证")
try:
    from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer
    analyzer = GEOAEOAnalyzer(doctor_name="张三", hospital="北京医院", department="心内科")

    # 测试1: 只有医院名，没有医生名 → 不应提及
    result = analyzer.analyze("北京医院是一家三甲医院。")
    assert result.geo_mentioned == False, f"医院名单独命中bug未修复: mentioned={result.geo_mentioned}"
    print(f"  PASS: 只有医院名 → mentioned={result.geo_mentioned} (期望False)")

    # 测试2: 医院+医生 → 应提及
    result = analyzer.analyze("1. 北京医院张三医生")
    assert result.geo_mentioned == True
    assert result.geo_rank == 1
    print(f"  PASS: 医院+医生 → mentioned={result.geo_mentioned}, rank={result.geo_rank} (期望True, 1)")

    # 测试3: 无序列表 → rank应为None
    result = analyzer.analyze("推荐张三医生。他很专业。")
    assert result.geo_mentioned == True
    assert result.geo_rank is None, f"无序列表rank应为None, 实际={result.geo_rank}"
    print(f"  PASS: 无序列表 → mentioned={result.geo_mentioned}, rank={result.geo_rank} (期望True, None)")

    print("  PASS: 分析器3个bug全部修复")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

db.close()
print("\n" + "=" * 60)
print("T06 端到端流程测试完成")
print("=" * 60)
