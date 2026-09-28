# 阶段四C执行手册：对标账号与竞品分析 + 审计日志 + 全局错误处理

> **执行模式**：新session执行，按需确认命令行操作
> **手册粒度**：B为主（函数/方法级别），关键改动用A（精确到行）
> **前置条件**：阶段四B已完成，工作区干净
> **Python路径**：`C:\Users\jenac\miniconda3\python.exe`（必须用这个）

---

## 一、阶段四C 目标

阶段四C包含三大模块：

### 模块1：对标账号管理与竞品对比分析
- 新建独立的 `BenchmarkAccount` 模型（不复用GEO监测的Competitor模型）
- 对标账号支持手动输入关键数据（粉丝数/平均阅读/最近文章）
- 数据采集留好接口（`data_source` 字段标记为 manual，后续可接入第三方数据平台自动替换）
- 竞品对比分析：数据概览对比+发文频率对比+爆款文章对比+AI差距分析

### 模块2：审计日志
- 新建 `AuditLog` 模型，记录用户关键操作
- 审计日志中间件，自动记录关键操作（登录/发布/删除/配置修改/数据导出）
- 审计日志API（管理员可查看所有用户，普通用户只能查看自己）
- 审计日志前端页面（列表+筛选+详情）

### 模块3：全局错误处理
- 新建统一异常处理中间件
- 统一错误码和错误响应格式
- 前端友好提示

**不做的（放到后续阶段）**：
- day_30快照和新指标体系（getarticletotaldetail，2025-11-01起数据，新旧指标映射复杂）
- 数据备份（SQLite备份可用简单脚本，不需做成系统功能）
- 主题分布对比（需要更复杂的AI分析和可视化）

---

## 二、改动文件清单

| 类型 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| 新建 | `backend/app/models/benchmark_account.py` | 新建 | 对标账号+对标文章模型 |
| 新建 | `backend/app/models/audit_log.py` | 新建 | 审计日志模型 |
| 新建 | `backend/app/models/competitor_analysis.py` | 新建 | 竞品对比分析结果模型 |
| 新建 | `backend/app/services/benchmark_service.py` | 新建 | 对标账号数据对比服务 |
| 新建 | `backend/app/services/competitor_analysis_service.py` | 新建 | 竞品AI分析服务 |
| 新建 | `backend/app/worker/competitor_analysis_tasks.py` | 新建 | 竞品分析异步任务 |
| 新建 | `backend/app/api/benchmark.py` | 新建 | 对标账号API |
| 新建 | `backend/app/api/audit.py` | 新建 | 审计日志API |
| 新建 | `backend/app/middleware/audit_middleware.py` | 新建 | 审计日志中间件 |
| 新建 | `backend/app/middleware/error_handler.py` | 新建 | 全局错误处理中间件 |
| 新建 | `backend/migrations/add_phase4c_tables.py` | 新建 | 数据库迁移脚本 |
| 新建 | `frontend/src/pages/BenchmarkAccounts.tsx` | 新建 | 对标账号管理页面 |
| 新建 | `frontend/src/pages/CompetitorAnalysis.tsx` | 新建 | 竞品对比分析页面 |
| 新建 | `frontend/src/pages/AuditLogs.tsx` | 新建 | 审计日志页面 |
| 修改 | `backend/app/models/__init__.py` | 修改 | 注册3个新模型 |
| 修改 | `backend/app/main.py` | 修改 | 注册2个中间件+2个路由 |
| 修改 | `backend/app/worker/worker.py` | 修改 | 注册新任务类型 |
| 修改 | `frontend/src/router/index.tsx` | 修改 | 注册3个新路由 |
| 修改 | `frontend/src/components/Layout.tsx` | 修改 | 菜单添加3个新入口（如适用） |

---

## 三、详细执行步骤

### 步骤1：新建对标账号模型

**文件**：`backend/app/models/benchmark_account.py`

```python
"""对标账号模型（内容运营模块，独立于GEO监测的Competitor模型）
- BenchmarkAccount: 对标公众号账号（手动输入数据，留好接口后续接入第三方）
- BenchmarkArticle: 对标账号的文章（手动输入）
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class BenchmarkAccount(Base):
    """对标公众号账号"""
    __tablename__ = "geo_benchmark_account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 账号基本信息
    account_name = Column(String(200), nullable=False)  # 公众号名称
    wechat_id = Column(String(100), default="")          # 微信号
    avatar_url = Column(String(500), default="")          # 头像URL
    description = Column(Text, default="")                 # 账号简介
    industry = Column(String(100), default="")             # 行业领域

    # 手动输入的关键数据（后续可由第三方数据平台自动更新）
    followers = Column(Integer, default=0)          # 粉丝数
    avg_reads = Column(Integer, default=0)           # 平均阅读量
    avg_likes = Column(Integer, default=0)            # 平均点赞数
    avg_shares = Column(Integer, default=0)           # 平均分享数
    weekly_posts = Column(Integer, default=0)         # 每周发文数

    # 数据来源标记（manual=手动输入，后续可改为 newrank/xigu 等第三方）
    data_source = Column(String(50), default="manual")
    last_updated = Column(DateTime(timezone=True), nullable=True)  # 数据最后更新时间

    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BenchmarkArticle(Base):
    """对标账号的文章（手动输入）"""
    __tablename__ = "geo_benchmark_article"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_id = Column(Integer, ForeignKey("geo_benchmark_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    title = Column(String(300), default="")       # 文章标题
    article_url = Column(String(500), default="")  # 文章URL
    publish_date = Column(Date, nullable=True, index=True)  # 发布日期

    # 手动输入的文章数据
    reads = Column(Integer, default=0)       # 阅读量
    likes = Column(Integer, default=0)        # 点赞数
    shares = Column(Integer, default=0)       # 分享数
    favorites = Column(Integer, default=0)    # 收藏数

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_benchmark_article_benchmark_date', 'benchmark_id', 'publish_date'),
    )
```

---

### 步骤2：新建审计日志模型

**文件**：`backend/app/models/audit_log.py`

```python
"""审计日志模型
记录用户关键操作，用于安全审计和操作追溯。
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "geo_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=True, index=True)  # 未登录时为null
    username = Column(String(100), default="")  # 冗余存储用户名，避免关联查询

    # 操作信息
    action = Column(String(50), nullable=False, index=True)  # 操作类型：login/logout/create/update/delete/export/publish/config
    resource_type = Column(String(50), default="")  # 资源类型：user/article/semantic/publish_account/benchmark/platform
    resource_id = Column(String(100), default="")    # 资源ID

    # 详情
    details = Column(Text, default="")  # 操作详情（JSON格式，记录变更前后的值等）
    ip_address = Column(String(50), default="")  # 客户端IP
    user_agent = Column(String(500), default="")  # 客户端User-Agent

    # 结果
    status = Column(String(20), default="success")  # success/failed
    error_message = Column(Text, default="")         # 失败时的错误信息

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index('ix_audit_log_user_action', 'user_id', 'action'),
        Index('ix_audit_log_created_at', 'created_at'),
    )
```

---

### 步骤3：新建竞品对比分析结果模型

**文件**：`backend/app/models/competitor_analysis.py`

```python
"""竞品对比分析结果模型（缓存AI分析结果，避免重复调用LLM）"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class CompetitorAnalysis(Base):
    """竞品对比分析结果"""
    __tablename__ = "geo_competitor_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)  # 自己的公众号账号
    benchmark_id = Column(Integer, ForeignKey("geo_benchmark_account.id"), nullable=False, index=True)  # 对标账号

    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    result_json = Column(Text, default="")  # 分析结果（JSON格式）
    failed_reason = Column(Text, default="")
    tokens_used = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_competitor_analysis_account_benchmark', 'account_id', 'benchmark_id', unique=True),
    )
```

---

### 步骤4：注册新模型

**文件**：`backend/app/models/__init__.py`

添加导入：
```python
from app.models.benchmark_account import BenchmarkAccount, BenchmarkArticle
from app.models.audit_log import AuditLog
from app.models.competitor_analysis import CompetitorAnalysis
```

并在 `__all__` 列表中添加 `BenchmarkAccount, BenchmarkArticle, AuditLog, CompetitorAnalysis`。

---

### 步骤5：数据库迁移脚本

**文件**：`backend/migrations/add_phase4c_tables.py`

```python
"""阶段四C数据库迁移：创建对标账号/审计日志/竞品分析表
运行方式：cd backend && C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.add_phase4c_tables
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models.benchmark_account import BenchmarkAccount, BenchmarkArticle
from app.models.audit_log import AuditLog
from app.models.competitor_analysis import CompetitorAnalysis

def upgrade():
    print("创建阶段四C数据表...")
    Base.metadata.create_all(bind=engine, tables=[
        BenchmarkAccount.__table__,
        BenchmarkArticle.__table__,
        AuditLog.__table__,
        CompetitorAnalysis.__table__,
    ])
    print("✅ 表创建完成")
    print("  - geo_benchmark_account (对标账号)")
    print("  - geo_benchmark_article (对标文章)")
    print("  - geo_audit_log (审计日志)")
    print("  - geo_competitor_analysis (竞品分析结果)")

if __name__ == "__main__":
    upgrade()
```

**执行迁移**：
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m migrations.add_phase4c_tables
```

---

### 步骤6：新建对标账号数据对比服务

**文件**：`backend/app/services/benchmark_service.py`

```python
"""对标账号数据对比服务
计算自己账号与对标账号的数据对比，用于竞品分析页面展示。
"""
import logging
from sqlalchemy.orm import Session
from app.models.publish_account import PublishAccount
from app.models.wechat_stats import WechatAccountStats, WechatArticle
from app.models.benchmark_account import BenchmarkAccount, BenchmarkArticle
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class BenchmarkService:
    """对标账号数据对比服务"""

    @staticmethod
    def get_account_summary(db: Session, account_id: int, user_id: int) -> dict:
        """获取自己账号的汇总数据（最近30天）"""
        account = db.query(PublishAccount).filter(
            PublishAccount.id == account_id,
            PublishAccount.user_id == user_id,
        ).first()
        if not account:
            raise ValueError("账号不存在")

        start_date = date.today() - timedelta(days=30)
        stats_list = db.query(WechatAccountStats).filter(
            WechatAccountStats.account_id == account_id,
            WechatAccountStats.stat_date >= start_date,
        ).all()

        if not stats_list:
            return {
                "account_name": account.account_name,
                "followers": 0,
                "avg_reads": 0,
                "avg_likes": 0,
                "avg_shares": 0,
                "weekly_posts": 0,
                "total_articles_30d": 0,
                "total_reads_30d": 0,
            }

        latest = max(stats_list, key=lambda s: s.stat_date)
        total_articles = sum(s.total_articles for s in stats_list)
        total_reads = sum(s.total_reads for s in stats_list)
        total_likes = sum(s.total_likes for s in stats_list)
        total_shares = sum(s.total_shares for s in stats_list)

        # 最近7天发文数
        week_start = date.today() - timedelta(days=7)
        week_stats = [s for s in stats_list if s.stat_date >= week_start]
        weekly_posts = sum(s.total_articles for s in week_stats)

        return {
            "account_name": account.account_name,
            "followers": latest.cumulate_users,
            "avg_reads": round(total_reads / total_articles) if total_articles > 0 else 0,
            "avg_likes": round(total_likes / total_articles) if total_articles > 0 else 0,
            "avg_shares": round(total_shares / total_articles) if total_articles > 0 else 0,
            "weekly_posts": weekly_posts,
            "total_articles_30d": total_articles,
            "total_reads_30d": total_reads,
        }

    @staticmethod
    def get_benchmark_summary(db: Session, benchmark_id: int, user_id: int) -> dict:
        """获取对标账号的汇总数据（手动输入）"""
        benchmark = db.query(BenchmarkAccount).filter(
            BenchmarkAccount.id == benchmark_id,
            BenchmarkAccount.user_id == user_id,
        ).first()
        if not benchmark:
            raise ValueError("对标账号不存在")

        return {
            "account_name": benchmark.account_name,
            "wechat_id": benchmark.wechat_id,
            "followers": benchmark.followers,
            "avg_reads": benchmark.avg_reads,
            "avg_likes": benchmark.avg_likes,
            "avg_shares": benchmark.avg_shares,
            "weekly_posts": benchmark.weekly_posts,
            "data_source": benchmark.data_source,
            "last_updated": benchmark.last_updated.isoformat() if benchmark.last_updated else None,
        }

    @staticmethod
    def get_top_articles(db: Session, account_id: int = None, benchmark_id: int = None,
                          user_id: int = None, limit: int = 5) -> list:
        """获取阅读量Top N文章（自己账号或对标账号）"""
        if account_id:
            # 自己账号：从WechatArticle+WechatArticleStats查询
            articles = db.query(WechatArticle).filter(
                WechatArticle.account_id == account_id,
                WechatArticle.user_id == user_id,
            ).all()

            result = []
            for article in articles:
                from app.models.wechat_stats import WechatArticleStats
                stats = db.query(WechatArticleStats).filter(
                    WechatArticleStats.article_id == article.id,
                    WechatArticleStats.snapshot_day == 0,
                ).first()
                result.append({
                    "title": article.title,
                    "publish_date": article.publish_date.isoformat() if article.publish_date else None,
                    "reads": stats.int_page_read_count if stats else 0,
                    "likes": stats.like_count if stats else 0,
                    "shares": stats.share_count if stats else 0,
                })
            result.sort(key=lambda x: x["reads"], reverse=True)
            return result[:limit]

        elif benchmark_id:
            # 对标账号：从BenchmarkArticle查询
            articles = db.query(BenchmarkArticle).filter(
                BenchmarkArticle.benchmark_id == benchmark_id,
                BenchmarkArticle.user_id == user_id,
            ).order_by(BenchmarkArticle.reads.desc()).limit(limit).all()

            return [{
                "title": a.title,
                "publish_date": a.publish_date.isoformat() if a.publish_date else None,
                "reads": a.reads,
                "likes": a.likes,
                "shares": a.shares,
            } for a in articles]

        return []

    @staticmethod
    def compare(db: Session, account_id: int, benchmark_id: int, user_id: int) -> dict:
        """生成对比数据（规则计算，不需要LLM）"""
        own = BenchmarkService.get_account_summary(db, account_id, user_id)
        benchmark = BenchmarkService.get_benchmark_summary(db, benchmark_id, user_id)

        # 计算差距百分比
        def gap_pct(own_val, bench_val):
            if bench_val == 0:
                return 0
            return round((own_val - bench_val) / bench_val * 100, 1)

        comparison = {
            "own": own,
            "benchmark": benchmark,
            "gaps": {
                "followers": gap_pct(own["followers"], benchmark["followers"]),
                "avg_reads": gap_pct(own["avg_reads"], benchmark["avg_reads"]),
                "avg_likes": gap_pct(own["avg_likes"], benchmark["avg_likes"]),
                "avg_shares": gap_pct(own["avg_shares"], benchmark["avg_shares"]),
                "weekly_posts": gap_pct(own["weekly_posts"], benchmark["weekly_posts"]),
            },
            "own_top_articles": BenchmarkService.get_top_articles(db, account_id=account_id, user_id=user_id),
            "benchmark_top_articles": BenchmarkService.get_top_articles(db, benchmark_id=benchmark_id, user_id=user_id),
        }

        return comparison
```

---

### 步骤7：新建竞品AI分析服务

**文件**：`backend/app/services/competitor_analysis_service.py`

```python
"""竞品对比AI分析服务
基于对比数据，调用LLM给出差距分析和改进建议。
"""
import json
import logging
from sqlalchemy.orm import Session
from app.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)


class CompetitorAnalysisService:
    """竞品对比AI分析服务"""

    @staticmethod
    def _get_llm_adapter(db: Session, user_id: int):
        """获取用户启用的LLM适配器（复用阶段四B的逻辑，注意实际字段名）"""
        from app.adapters import adapter_factory
        from app.models.user_platform_pref import UserPlatformPref

        enabled_prefs = db.query(UserPlatformPref).filter(
            UserPlatformPref.user_id == user_id,
            UserPlatformPref.enabled == True,
        ).all()

        if not enabled_prefs:
            platforms = adapter_factory.get_enabled_platforms()
            if not platforms:
                raise ValueError("未配置任何可用的AI平台")
            return adapter_factory.get_adapter(platforms[0])

        for pref in enabled_prefs:
            adapter = adapter_factory.get_adapter(pref.platform_code)
            if adapter:
                return adapter

        raise ValueError("未找到可用的AI平台适配器")

    @classmethod
    def analyze(cls, db: Session, account_id: int, benchmark_id: int, user_id: int) -> dict:
        """执行竞品对比AI分析"""
        # 1. 获取对比数据
        comparison = BenchmarkService.compare(db, account_id, benchmark_id, user_id)

        # 2. 获取LLM适配器
        adapter = cls._get_llm_adapter(db, user_id)

        # 3. 构造prompt
        own = comparison["own"]
        benchmark = comparison["benchmark"]
        gaps = comparison["gaps"]

        own_top = comparison["own_top_articles"][:3]
        bench_top = comparison["benchmark_top_articles"][:3]

        prompt = f"""你是一位资深的医疗行业微信公众号运营专家。请根据以下数据，对自己账号与对标账号进行深度对比分析，并给出可操作的改进建议。

## 自己账号数据
- 账号名称：{own['account_name']}
- 粉丝数：{own['followers']}
- 平均阅读量：{own['avg_reads']}
- 平均点赞：{own['avg_likes']}
- 平均分享：{own['avg_shares']}
- 每周发文数：{own['weekly_posts']}
- 近30天发文数：{own['total_articles_30d']}
- 近30天总阅读：{own['total_reads_30d']}

## 对标账号数据
- 账号名称：{benchmark['account_name']}
- 微信号：{benchmark.get('wechat_id', '')}
- 粉丝数：{benchmark['followers']}
- 平均阅读量：{benchmark['avg_reads']}
- 平均点赞：{benchmark['avg_likes']}
- 平均分享：{benchmark['avg_shares']}
- 每周发文数：{benchmark['weekly_posts']}

## 差距分析（正数表示领先，负数表示落后）
- 粉丝数差距：{gaps['followers']}%
- 平均阅读差距：{gaps['avg_reads']}%
- 平均点赞差距：{gaps['avg_likes']}%
- 平均分享差距：{gaps['avg_shares']}%
- 发文频率差距：{gaps['weekly_posts']}%

## 自己账号爆款文章Top3
{chr(10).join(f'- {a["title"]}（阅读{a["reads"]}，点赞{a["likes"]}，分享{a["shares"]}）' for a in own_top) if own_top else '（暂无数据）'}

## 对标账号爆款文章Top3
{chr(10).join(f'- {a["title"]}（阅读{a["reads"]}，点赞{a["likes"]}，分享{a["shares"]}）' for a in bench_top) if bench_top else '（暂无数据）'}

## 请按以下JSON格式输出分析结果
{{
  "overall_assessment": "整体评估（100字以内）",
  "strengths": ["自己账号的优势1", "优势2", "优势3"],
  "weaknesses": ["自己账号的不足1", "不足2", "不足3"],
  "gap_analysis": {{
    "content_quality": "内容质量差距分析",
    "publishing_frequency": "发文频率差距分析",
    "engagement": "互动率差距分析",
    "audience_scale": "粉丝规模差距分析"
  }},
  "improvement_suggestions": [
    {{"area": "改进领域1", "suggestion": "具体建议", "priority": "high/medium/low", "expected_effect": "预期效果"}},
    {{"area": "改进领域2", "suggestion": "具体建议", "priority": "high/medium/low", "expected_effect": "预期效果"}},
    {{"area": "改进领域3", "suggestion": "具体建议", "priority": "high/medium/low", "expected_effect": "预期效果"}}
  ],
  "content_direction": "未来内容方向建议（100字以内）"
}}

请直接输出JSON，不要输出其他内容。"""

        system_prompt = "你是一位资深的医疗行业微信公众号运营专家，擅长竞品分析和内容优化。输出必须是严格的JSON格式。"

        logger.info(f"[竞品AI分析] 开始LLM分析，account_id={account_id}, benchmark_id={benchmark_id}")
        result = adapter.query(prompt, system_prompt=system_prompt)

        # 解析LLM输出（注意adapter.query()返回QueryResult对象，用.answer取内容）
        llm_result = {}
        try:
            content = result.answer if hasattr(result, 'answer') else str(result)
            json_start = content.find("{")
            json_end = content.rfind("}")
            if json_start >= 0 and json_end > json_start:
                llm_result = json.loads(content[json_start:json_end+1])
        except Exception as e:
            logger.warning(f"[竞品AI分析] LLM输出解析失败: {e}")
            llm_result = {"raw_output": str(result)[:500]}

        # 合并对比数据和LLM分析
        final_result = {
            "comparison": comparison,
            "llm_analysis": llm_result,
        }

        return final_result
```

---

### 步骤8：新建竞品分析异步任务

**文件**：`backend/app/worker/competitor_analysis_tasks.py`

```python
"""竞品对比分析异步任务"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.competitor_analysis import CompetitorAnalysis
from app.services.competitor_analysis_service import CompetitorAnalysisService
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_competitor_analysis(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理竞品对比分析任务"""
    payload = json.loads(task.payload_json or "{}")
    account_id = payload.get("account_id")
    benchmark_id = payload.get("benchmark_id")

    if not account_id or not benchmark_id:
        raise ValueError("payload 中缺少 account_id 或 benchmark_id")

    if on_progress:
        on_progress(1, 3, "查询对比数据")

    try:
        if on_progress:
            on_progress(2, 3, "LLM分析中（约10-30秒）")

        result = CompetitorAnalysisService.analyze(db, account_id, benchmark_id, task.created_by)

        if on_progress:
            on_progress(3, 3, "分析完成，保存结果")

        # 保存分析结果
        analysis_record = db.query(CompetitorAnalysis).filter(
            CompetitorAnalysis.account_id == account_id,
            CompetitorAnalysis.benchmark_id == benchmark_id,
        ).first()

        if analysis_record:
            analysis_record.result_json = json.dumps(result, ensure_ascii=False)
            analysis_record.status = "completed"
            analysis_record.completed_at = datetime.now()
        else:
            analysis_record = CompetitorAnalysis(
                user_id=task.created_by,
                account_id=account_id,
                benchmark_id=benchmark_id,
                status="completed",
                result_json=json.dumps(result, ensure_ascii=False),
                completed_at=datetime.now(),
            )
            db.add(analysis_record)

        db.commit()
        return {"account_id": account_id, "benchmark_id": benchmark_id, "status": "completed"}

    except Exception as e:
        # 失败时更新记录状态
        logger.error(f"[竞品AI分析] 失败: {e}")
        analysis_record = db.query(CompetitorAnalysis).filter(
            CompetitorAnalysis.account_id == account_id,
            CompetitorAnalysis.benchmark_id == benchmark_id,
        ).first()
        if analysis_record:
            analysis_record.status = "failed"
            analysis_record.failed_reason = str(e)
            analysis_record.completed_at = datetime.now()
            db.commit()
        raise
```

---

### 步骤9：注册新任务类型到 Worker

**文件**：`backend/app/worker/worker.py`

**修改1**：在导入区域添加：
```python
import app.worker.competitor_analysis_tasks  # noqa: F401
```

**修改2**：在 `TASK_TIMEOUT_BY_TYPE` 字典中添加：
```python
"competitor_analysis": 300,  # 竞品对比AI分析：5分钟
```

---

### 步骤10：新建对标账号API

**文件**：`backend/app/api/benchmark.py`

```python
"""对标账号管理API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id, require_admin
from app.models.benchmark_account import BenchmarkAccount, BenchmarkArticle
from app.models.competitor_analysis import CompetitorAnalysis
from app.models.task import AsyncTask
import json

router = APIRouter(prefix="/api/v1/benchmark", tags=["对标账号"])


# ===== Pydantic 模型 =====

class BenchmarkCreate(BaseModel):
    account_name: str = Field(..., description="公众号名称")
    wechat_id: str = Field("", description="微信号")
    description: str = Field("", description="账号简介")
    industry: str = Field("", description="行业领域")
    followers: int = Field(0, description="粉丝数")
    avg_reads: int = Field(0, description="平均阅读量")
    avg_likes: int = Field(0, description="平均点赞数")
    avg_shares: int = Field(0, description="平均分享数")
    weekly_posts: int = Field(0, description="每周发文数")
    note: str = Field("", description="备注")


class BenchmarkUpdate(BaseModel):
    account_name: Optional[str] = None
    wechat_id: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    followers: Optional[int] = None
    avg_reads: Optional[int] = None
    avg_likes: Optional[int] = None
    avg_shares: Optional[int] = None
    weekly_posts: Optional[int] = None
    note: Optional[str] = None


class BenchmarkArticleCreate(BaseModel):
    title: str = Field(..., description="文章标题")
    article_url: str = Field("", description="文章URL")
    publish_date: Optional[date] = None
    reads: int = Field(0, description="阅读量")
    likes: int = Field(0, description="点赞数")
    shares: int = Field(0, description="分享数")
    favorites: int = Field(0, description="收藏数")


# ===== 对标账号 CRUD =====

@router.get("", summary="获取我的对标账号列表")
def list_benchmarks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    items = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.user_id == user_id
    ).order_by(BenchmarkAccount.created_at.desc()).all()

    result = [{
        "id": b.id,
        "account_name": b.account_name,
        "wechat_id": b.wechat_id,
        "description": b.description,
        "industry": b.industry,
        "followers": b.followers,
        "avg_reads": b.avg_reads,
        "avg_likes": b.avg_likes,
        "avg_shares": b.avg_shares,
        "weekly_posts": b.weekly_posts,
        "data_source": b.data_source,
        "last_updated": b.last_updated.isoformat() if b.last_updated else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    } for b in items]

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.post("", summary="添加对标账号")
def create_benchmark(
    data: BenchmarkCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = BenchmarkAccount(
        user_id=user_id,
        account_name=data.account_name,
        wechat_id=data.wechat_id,
        description=data.description,
        industry=data.industry,
        followers=data.followers,
        avg_reads=data.avg_reads,
        avg_likes=data.avg_likes,
        avg_shares=data.avg_shares,
        weekly_posts=data.weekly_posts,
        note=data.note,
        last_updated=datetime.now(),
    )
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)
    return {"code": 0, "message": "success", "data": {"id": benchmark.id}}


@router.put("/{benchmark_id}", summary="更新对标账号")
def update_benchmark(
    benchmark_id: int,
    data: BenchmarkUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(benchmark, field, value)
    benchmark.last_updated = datetime.now()
    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{benchmark_id}", summary="删除对标账号")
def delete_benchmark(
    benchmark_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    # 级联删除对标文章
    db.query(BenchmarkArticle).filter(BenchmarkArticle.benchmark_id == benchmark_id).delete()
    db.delete(benchmark)
    db.commit()
    return {"code": 0, "message": "success"}


# ===== 对标文章 CRUD =====

@router.get("/{benchmark_id}/articles", summary="获取对标账号文章列表")
def list_benchmark_articles(
    benchmark_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    query = db.query(BenchmarkArticle).filter(BenchmarkArticle.benchmark_id == benchmark_id)
    total = query.count()
    articles = query.order_by(BenchmarkArticle.publish_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [{
        "id": a.id,
        "title": a.title,
        "article_url": a.article_url,
        "publish_date": a.publish_date.isoformat() if a.publish_date else None,
        "reads": a.reads,
        "likes": a.likes,
        "shares": a.shares,
        "favorites": a.favorites,
    } for a in articles]

    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/{benchmark_id}/articles", summary="添加对标文章")
def create_benchmark_article(
    benchmark_id: int,
    data: BenchmarkArticleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    article = BenchmarkArticle(
        benchmark_id=benchmark_id,
        user_id=user_id,
        title=data.title,
        article_url=data.article_url,
        publish_date=data.publish_date,
        reads=data.reads,
        likes=data.likes,
        shares=data.shares,
        favorites=data.favorites,
    )
    db.add(article)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": article.id}}


@router.delete("/{benchmark_id}/articles/{article_id}", summary="删除对标文章")
def delete_benchmark_article(
    benchmark_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(BenchmarkArticle).filter(
        BenchmarkArticle.id == article_id,
        BenchmarkArticle.benchmark_id == benchmark_id,
        BenchmarkArticle.user_id == user_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"code": 0, "message": "success"}


# ===== 竞品对比分析 =====

@router.get("/analysis/compare", summary="获取对比数据（规则计算）")
def get_comparison(
    account_id: int = Query(...),
    benchmark_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    from app.services.benchmark_service import BenchmarkService
    result = BenchmarkService.compare(db, account_id, benchmark_id, user_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/analysis", summary="提交竞品AI分析")
def submit_competitor_analysis(
    account_id: int = Query(...),
    benchmark_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 检查是否已有正在处理的分析
    existing_task = db.query(AsyncTask).filter(
        AsyncTask.task_type == "competitor_analysis",
        AsyncTask.status.in_(["queued", "running"]),
        AsyncTask.created_by == user_id,
    ).first()
    if existing_task:
        return {"code": 0, "message": "已有分析任务在执行中", "data": {"task_id": existing_task.id}}

    # 创建异步任务
    task = AsyncTask(
        task_type="competitor_analysis",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({"account_id": account_id, "benchmark_id": benchmark_id}, ensure_ascii=False),
        progress_message="竞品对比AI分析中",
    )
    db.add(task)

    # 更新分析记录状态
    analysis_record = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.account_id == account_id,
        CompetitorAnalysis.benchmark_id == benchmark_id,
    ).first()
    if analysis_record:
        analysis_record.status = "processing"
    else:
        analysis_record = CompetitorAnalysis(
            user_id=user_id,
            account_id=account_id,
            benchmark_id=benchmark_id,
            status="processing",
        )
        db.add(analysis_record)
    db.commit()

    return {"code": 0, "message": "分析任务已提交，约10-30秒后完成", "data": {"task_id": task.id}}


@router.get("/analysis", summary="获取竞品AI分析结果")
def get_competitor_analysis(
    account_id: int = Query(...),
    benchmark_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    analysis = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.account_id == account_id,
        CompetitorAnalysis.benchmark_id == benchmark_id,
        CompetitorAnalysis.user_id == user_id,
    ).order_by(CompetitorAnalysis.created_at.desc()).first()

    if not analysis:
        return {"code": 0, "message": "success", "data": {"status": "none", "result": None}}

    result_data = None
    if analysis.status == "completed" and analysis.result_json:
        try:
            result_data = json.loads(analysis.result_json)
        except Exception:
            result_data = None

    return {"code": 0, "message": "success", "data": {
        "status": analysis.status,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "result": result_data,
        "failed_reason": analysis.failed_reason,
    }}
```

---

### 步骤11：新建审计日志中间件

**文件**：`backend/app/middleware/audit_middleware.py`

```python
"""审计日志中间件
自动记录用户关键操作（登录/发布/删除/配置修改/数据导出）。
"""
import logging
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# 需要记录审计日志的路径模式（正则匹配）
AUDIT_PATTERNS = {
    # 登录登出
    ("/api/v1/auth/local/login", "POST"): "login",
    ("/api/v1/auth/logout", "POST"): "logout",
    ("/api/v1/auth/iam/callback", "GET"): "login",
    # 发布相关
    ("/api/v1/distribution/publish", "POST"): "publish",
    ("/api/v1/distribution/.*/publish", "POST"): "publish",
    # 删除操作（通用匹配）
    (".*", "DELETE"): "delete",
    # 数据导出
    ("/api/v1/export/.*", "GET"): "export",
    ("/api/v1/publish-accounts/.*/articles/export", "GET"): "export",
    # 平台配置修改
    ("/api/v1/platforms/.*/toggle", "POST"): "config",
    ("/api/v1/platforms/.*", "PUT"): "config",
    # 发布账号修改
    ("/api/v1/publish-accounts", "POST"): "create",
    ("/api/v1/publish-accounts/.*", "PUT"): "update",
    # 对标账号修改
    ("/api/v1/benchmark", "POST"): "create",
    ("/api/v1/benchmark/.*", "PUT"): "update",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""

    async def dispatch(self, request: Request, call_next):
        # 先执行请求，获取响应状态
        response = await call_next(request)

        try:
            path = request.url.path
            method = request.method

            # 匹配需要记录的操作
            action = None
            for (pattern, pat_method), act in AUDIT_PATTERNS.items():
                if method == pat_method:
                    import re
                    if re.fullmatch(pattern, path):
                        action = act
                        break

            if not action:
                return response

            # 只记录成功的操作（状态码2xx）
            if response.status_code >= 300:
                return response

            # 获取用户信息（从request.state，由auth中间件设置）
            user_id = getattr(request.state, "user_id", None)
            username = getattr(request.state, "username", "")

            # 获取客户端信息
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "")

            # 提取资源类型和ID
            resource_type = self._extract_resource_type(path)
            resource_id = self._extract_resource_id(path)

            # 异步写入数据库（在后台线程中执行，避免阻塞响应）
            self._save_audit_log(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=client_ip,
                user_agent=user_agent,
                status="success",
            )

        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return response

    @staticmethod
    def _extract_resource_type(path: str) -> str:
        """从URL路径提取资源类型"""
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            return parts[2]  # /api/v1/{resource_type}/...
        return ""

    @staticmethod
    def _extract_resource_id(path: str) -> str:
        """从URL路径提取资源ID"""
        parts = path.strip("/").split("/")
        # 查找数字ID部分
        for part in parts:
            if part.isdigit():
                return part
        return ""

    @staticmethod
    def _save_audit_log(**kwargs):
        """保存审计日志到数据库"""
        try:
            db = SessionLocal()
            log = AuditLog(**kwargs)
            db.add(log)
            db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"保存审计日志失败: {e}")
```

---

### 步骤12：新建全局错误处理中间件

**文件**：`backend/app/middleware/error_handler.py`

```python
"""全局错误处理中间件
统一异常处理，统一错误码和错误响应格式。
"""
import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            # 请求参数验证错误
            logger.warning(f"请求参数验证错误: {e.errors()}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "code": 422,
                    "message": "请求参数错误",
                    "errors": e.errors(),
                }
            )
        except ValueError as e:
            # 业务逻辑错误
            logger.warning(f"业务逻辑错误: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "code": 400,
                    "message": str(e),
                }
            )
        except PermissionError as e:
            # 权限错误
            logger.warning(f"权限错误: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "code": 403,
                    "message": "没有权限执行此操作",
                }
            )
        except Exception as e:
            # 未捕获的异常
            error_detail = traceback.format_exc()
            logger.error(f"未捕获的异常: {e}\n{error_detail}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": 500,
                    "message": "服务器内部错误，请稍后重试",
                    "error_type": type(e).__name__,
                }
            )
```

---

### 步骤13：新建审计日志API

**文件**：`backend/app/api/audit.py`

```python
"""审计日志API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id, require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/audit", tags=["审计日志"])


@router.get("", summary="获取审计日志列表")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int = Query(None, description="按用户筛选（管理员可用）"),
    action: str = Query(None, description="按操作类型筛选"),
    resource_type: str = Query(None, description="按资源类型筛选"),
    start_date: str = Query(None, description="开始日期（YYYY-MM-DD）"),
    end_date: str = Query(None, description="结束日期（YYYY-MM-DD）"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # 普通用户只能查看自己的日志，管理员可查看所有
    query = db.query(AuditLog)

    # 检查是否是管理员
    current_user = db.query(User).filter(User.id == current_user_id).first()
    is_admin = current_user and current_user.role == "admin"

    if not is_admin:
        query = query.filter(AuditLog.user_id == current_user_id)
    elif user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AuditLog.created_at <= datetime.fromisoformat(end_date) + timedelta(days=1))

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [{
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in logs]

    return {"code": 0, "message": "success", "data": {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "is_admin": is_admin,
    }}


@router.get("/actions", summary="获取操作类型列表")
def get_action_types():
    """获取所有操作类型（用于筛选下拉框）"""
    actions = [
        {"value": "login", "label": "登录"},
        {"value": "logout", "label": "登出"},
        {"value": "create", "label": "创建"},
        {"value": "update", "label": "更新"},
        {"value": "delete", "label": "删除"},
        {"value": "publish", "label": "发布"},
        {"value": "export", "label": "导出"},
        {"value": "config", "label": "配置修改"},
    ]
    return {"code": 0, "message": "success", "data": {"items": actions}}
```

---

### 步骤14：注册中间件和路由到 main.py

**文件**：`backend/app/main.py`

**修改1**：在导入区域添加：
```python
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
```

**修改2**：在 `app.add_middleware(RateLimitMiddleware, ...)` 之后添加：
```python
# 全局错误处理中间件（必须在最外层，最先捕获异常）
app.add_middleware(ErrorHandlerMiddleware)
# 审计日志中间件
app.add_middleware(AuditMiddleware)
```

注意：中间件的执行顺序是反向的（后添加的先执行），所以ErrorHandlerMiddleware应该最后添加（最先执行），AuditMiddleware在ErrorHandler之前添加。

**修改3**：在路由注册区域添加：
```python
from app.api.benchmark import router as benchmark_router
from app.api.audit import router as audit_router
app.include_router(benchmark_router)
app.include_router(audit_router)
```

---

### 步骤15：新建对标账号管理前端页面

**文件**：`frontend/src/pages/BenchmarkAccounts.tsx`

```tsx
import { useState, useEffect } from 'react'
import {
  Card, Table, Button, Space, Modal, Form, Input, InputNumber,
  message, Popconfirm, Tag, Row, Col, Statistic
} from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, BarChartOutlined } from '@ant-design/icons'
import request from '@/api'
import { useNavigate } from 'react-router-dom'

const { TextArea } = Input

const BenchmarkAccounts = () => {
  const navigate = useNavigate()
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadList = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/benchmark')
      setList(res.data?.items || [])
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadList() }, [])

  const handleCreate = async (values: any) => {
    try {
      if (editingId) {
        await request.put(`/benchmark/${editingId}`, values)
        message.success('更新成功')
      } else {
        await request.post('/benchmark', values)
        message.success('添加成功')
      }
      setModalVisible(false)
      setEditingId(null)
      form.resetFields()
      loadList()
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const handleEdit = (record: any) => {
    setEditingId(record.id)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/benchmark/${id}`)
      message.success('删除成功')
      loadList()
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const columns = [
    { title: '公众号名称', dataIndex: 'account_name', key: 'account_name' },
    { title: '微信号', dataIndex: 'wechat_id', key: 'wechat_id' },
    { title: '粉丝数', dataIndex: 'followers', key: 'followers', render: (v: number) => v.toLocaleString() },
    { title: '平均阅读', dataIndex: 'avg_reads', key: 'avg_reads', render: (v: number) => v.toLocaleString() },
    { title: '每周发文', dataIndex: 'weekly_posts', key: 'weekly_posts' },
    { title: '数据来源', dataIndex: 'data_source', key: 'data_source', render: (v: string) => <Tag color={v === 'manual' ? 'orange' : 'blue'}>{v === 'manual' ? '手动输入' : v}</Tag> },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: any, record: any) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" icon={<BarChartOutlined />} onClick={() => navigate('/competitor-analysis')}>对比分析</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="对标账号管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingId(null); form.resetFields(); setModalVisible(true) }}>
            添加对标账号
          </Button>
        }
      >
        <Table columns={columns} dataSource={list} rowKey="id" loading={loading} />
      </Card>

      <Modal
        title={editingId ? '编辑对标账号' : '添加对标账号'}
        open={modalVisible}
        onCancel={() => { setModalVisible(false); setEditingId(null) }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="account_name" label="公众号名称" rules={[{ required: true, message: '请输入公众号名称' }]}>
                <Input placeholder="请输入公众号名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="wechat_id" label="微信号">
                <Input placeholder="请输入微信号" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="账号简介">
            <TextArea rows={2} placeholder="请输入账号简介" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="followers" label="粉丝数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="avg_reads" label="平均阅读量">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="weekly_posts" label="每周发文数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="avg_likes" label="平均点赞数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="avg_shares" label="平均分享数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="note" label="备注">
            <TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">{editingId ? '保存' : '添加'}</Button>
              <Button onClick={() => { setModalVisible(false); setEditingId(null) }}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default BenchmarkAccounts
```

---

### 步骤16：新建竞品对比分析前端页面

**文件**：`frontend/src/pages/CompetitorAnalysis.tsx`

由于页面较长，这里给出核心结构和关键组件。新session执行时需要完整实现。

**核心功能**：
1. 选择自己的公众号账号（下拉）
2. 选择对标账号（下拉）
3. 数据概览对比卡片（自己 vs 对标，含差距百分比）
4. 发文频率对比柱状图
5. 爆款文章对比表格（双方Top5）
6. AI差距分析（手动触发，结果缓存，4个Tab展示）

**关键代码结构**：

```tsx
// 状态
const [ownAccountId, setOwnAccountId] = useState<number | null>(null)
const [benchmarkId, setBenchmarkId] = useState<number | null>(null)
const [comparison, setComparison] = useState<any>(null)
const [analysis, setAnalysis] = useState<any>(null)
const [analyzing, setAnalyzing] = useState(false)

// 加载对比数据（规则计算，立即返回）
const loadComparison = async () => {
  const res = await request.get('/benchmark/analysis/compare', { params: { account_id: ownAccountId, benchmark_id } })
  setComparison(res.data)
}

// 提交AI分析
const handleAnalyze = async () => {
  setAnalyzing(true)
  await request.post('/benchmark/analysis', null, { params: { account_id: ownAccountId, benchmark_id } })
  // 轮询结果
  setTimeout(() => loadAnalysis(), 3000)
}

// 渲染：对比卡片 + 差距百分比（正数绿色领先，负数红色落后）
// 渲染：发文频率对比柱状图（ECharts）
// 渲染：爆款文章对比表格
// 渲染：AI分析结果（整体评估/优势/不足/改进建议/内容方向）
```

新session执行时需要完整实现这个页面，包括ECharts图表和AI分析结果的4个Tab展示。

---

### 步骤17：新建审计日志前端页面

**文件**：`frontend/src/pages/AuditLogs.tsx`

**核心功能**：
1. 审计日志列表表格（时间/用户/操作类型/资源/IP/状态）
2. 筛选（用户/操作类型/时间范围，管理员可筛选所有用户）
3. 操作类型中文映射
4. 分页

**关键代码结构**：

```tsx
const ACTION_MAP: Record<string, { label: string; color: string }> = {
  login: { label: '登录', color: 'green' },
  logout: { label: '登出', color: 'default' },
  create: { label: '创建', color: 'blue' },
  update: { label: '更新', color: 'orange' },
  delete: { label: '删除', color: 'red' },
  publish: { label: '发布', color: 'purple' },
  export: { label: '导出', color: 'cyan' },
  config: { label: '配置修改', color: 'gold' },
}

// 列：时间/用户名/操作类型/资源类型/资源ID/IP/状态
// 筛选：操作类型下拉 + 日期范围选择器 + 用户下拉（管理员可见）
```

---

### 步骤18：注册前端路由和菜单

**文件**：`frontend/src/router/index.tsx`

添加3个路由：
```tsx
<Route path="/benchmark-accounts" element={<BenchmarkAccounts />} />
<Route path="/competitor-analysis" element={<CompetitorAnalysis />} />
<Route path="/audit-logs" element={<AuditLogs />} />
```

**菜单**：在Layout组件的菜单中添加3个入口（如适用）：
- 对标账号管理（内容运营分组下）
- 竞品对比分析（内容运营分组下）
- 审计日志（系统管理分组下，仅管理员可见）

---

## 四、验证清单

### 后端验证

1. **数据库迁移**：运行迁移脚本，确认4张表创建成功
2. **后端import检查**：`from app.main import app` 通过
3. **后端启动**：无ERROR，2个新中间件注册成功，2个新路由注册成功
4. **API测试**：
   - 对标账号CRUD：POST/PUT/GET/DELETE /api/v1/benchmark
   - 对标文章CRUD：POST/GET/DELETE /api/v1/benchmark/{id}/articles
   - 对比数据：GET /api/v1/benchmark/analysis/compare?account_id=1&benchmark_id=1
   - 提交AI分析：POST /api/v1/benchmark/analysis?account_id=1&benchmark_id=1
   - 获取分析结果：GET /api/v1/benchmark/analysis?account_id=1&benchmark_id=1
   - 审计日志：GET /api/v1/audit（普通用户只能看自己，管理员可看所有）
   - 操作类型列表：GET /api/v1/audit/actions

### 前端验证

1. **前端tsc检查**：npx tsc --noEmit（本次改动文件零错误）
2. **前端打包**：npx vite build 成功
3. **页面测试**：
   - 对标账号管理页：添加/编辑/删除对标账号，手动输入数据
   - 竞品对比分析页：选择账号和对标账号，查看对比数据，提交AI分析，查看分析结果
   - 审计日志页：查看操作日志，筛选功能正常
   - 菜单：3个新页面入口正常显示

### 功能验证

1. **审计日志自动记录**：登录/发布/删除/导出等操作后，审计日志表中有对应记录
2. **全局错误处理**：触发一个异常（如访问不存在的资源），返回统一格式的错误响应
3. **竞品AI分析**：提交分析后，约10-30秒后显示分析结果，包含整体评估/优势/不足/改进建议
4. **用户隔离**：普通用户只能查看自己的对标账号和审计日志

---

## 五、注意事项

1. **审计日志中间件顺序**：ErrorHandlerMiddleware必须在最外层（最后add_middleware），确保能捕获所有异常。AuditMiddleware在ErrorHandler之内。

2. **审计日志性能**：审计日志写入是同步的，可能略微影响响应时间。对于高并发场景，后续可以改为异步写入或批量写入。当前50用户规模无性能问题。

3. **对标账号数据来源**：当前只有manual（手动输入）。data_source字段预留了第三方数据平台接入能力，后续可以改为newrank/xigu等。

4. **竞品分析结果缓存**：分析结果存储在competitor_analysis表中，唯一键是(account_id, benchmark_id)。重新分析会覆盖旧结果。

5. **全局错误处理与现有异常的兼容**：现有的HTTPException（如404/401）由FastAPI默认处理，ErrorHandlerMiddleware只处理未捕获的异常。需要确认两者不冲突。

6. **前端页面完整实现**：步骤16（竞品对比分析页）和步骤17（审计日志页）只给出了核心结构，新session执行时需要完整实现所有功能，包括ECharts图表、表单、表格、筛选等。

---

## 六、Git 提交

完成所有改动并验证通过后：

```bash
cd C:\Users\jenac\Desktop\GEO
git add backend/app/models/benchmark_account.py
git add backend/app/models/audit_log.py
git add backend/app/models/competitor_analysis.py
git add backend/app/models/__init__.py
git add backend/app/services/benchmark_service.py
git add backend/app/services/competitor_analysis_service.py
git add backend/app/worker/competitor_analysis_tasks.py
git add backend/app/worker/worker.py
git add backend/app/api/benchmark.py
git add backend/app/api/audit.py
git add backend/app/middleware/audit_middleware.py
git add backend/app/middleware/error_handler.py
git add backend/app/main.py
git add backend/migrations/add_phase4c_tables.py
git add frontend/src/pages/BenchmarkAccounts.tsx
git add frontend/src/pages/CompetitorAnalysis.tsx
git add frontend/src/pages/AuditLogs.tsx
git add frontend/src/router/index.tsx
git add frontend/src/components/Layout.tsx  # 如修改
git commit -m "feat: 阶段四C-对标账号与竞品分析+审计日志+全局错误处理（12项）"
```

---

**手册结束。执行过程中有任何不明白、不确定的事项，主动提出讨论。**

**特别提醒**：步骤16（竞品对比分析页）和步骤17（审计日志页）只给出了核心结构，执行时需要完整实现所有UI组件和交互逻辑。
