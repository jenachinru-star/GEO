# 阶段四A执行手册：微信公众号数据采集与账号概览

> **执行模式**：新session执行，按需确认命令行操作
> **手册粒度**：B为主（函数/方法级别），关键改动用A（精确到行）
> **前置条件**：阶段一至阶段三C全部完成（commit 80908f6），工作区干净
> **Python路径**：`C:\Users\jenac\miniconda3\python.exe`（必须用这个）

---

## 一、阶段四A 目标

为微信公众号发布账号增加**数据采集与监测能力**，通过微信官方API自动采集账号数据（粉丝/文章/阅读量），并在前端展示数据概览。同时完善微信发布器（封面图+真实URL）和发布账号真实验证。

**交付物**：
- 3个新数据库表（账号每日统计/文章基本信息/文章数据快照）
- 1个数据采集服务（wechat_data_service.py）
- 1个异步任务（wechat_data_tasks.py）
- 1个定时任务（每天凌晨2点自动采集）
- 5个新API（概览/趋势/文章列表/文章详情/手动采集）
- 1个前端页面（账号数据概览）
- 微信发布器完善（封面图上传+发布状态轮询）
- 发布账号真实验证（调用微信API）

---

## 二、改动文件清单

| 类型 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| 新建 | `backend/app/models/wechat_stats.py` | 新建 | 3个数据模型 |
| 新建 | `backend/app/services/wechat_data_service.py` | 新建 | 微信数据采集服务 |
| 新建 | `backend/app/worker/wechat_data_tasks.py` | 新建 | 数据采集异步任务 |
| 新建 | `backend/migrations/add_wechat_stats_tables.py` | 新建 | 数据库迁移脚本 |
| 新建 | `frontend/src/pages/WechatAccountStats.tsx` | 新建 | 账号数据概览页面 |
| 修改 | `backend/app/models/__init__.py` | 修改 | 注册新模型 |
| 修改 | `backend/app/api/publish_account.py` | 修改 | 新增5个API+真实验证 |
| 修改 | `backend/app/publishers/wechat.py` | 修改 | 封面图上传+发布状态轮询 |
| 修改 | `backend/app/worker/worker.py` | 修改 | 注册新任务类型+导入 |
| 修改 | `backend/app/main.py` | 修改 | 新增定时采集任务 |
| 修改 | `frontend/src/pages/PublishAccounts.tsx` | 修改 | 增加"查看数据"按钮 |
| 修改 | `frontend/src/App.tsx` | 修改 | 注册新路由 |

---

## 三、详细执行步骤

### 步骤1：新建数据库模型

**文件**：`backend/app/models/wechat_stats.py`

```python
"""微信公众号数据统计模型
- WechatAccountStats: 账号每日统计快照
- WechatArticle: 文章基本信息（静态）
- WechatArticleStats: 文章数据快照（发布后1/3/7/30天）
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Float, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class WechatAccountStats(Base):
    """微信公众号账号每日统计快照"""
    __tablename__ = "geo_wechat_account_stats"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    stat_date = Column(Date, nullable=False, index=True)  # 统计日期

    # 用户数据
    new_users = Column(Integer, default=0)       # 新增关注
    cancel_users = Column(Integer, default=0)    # 取消关注
    net_growth = Column(Integer, default=0)      # 净增
    cumulate_users = Column(Integer, default=0)  # 累计关注用户数

    # 图文数据
    total_articles = Column(Integer, default=0)  # 当天发文数
    total_reads = Column(Integer, default=0)     # 总阅读次数
    total_read_users = Column(Integer, default=0)  # 总阅读人数
    total_shares = Column(Integer, default=0)    # 总分享次数
    total_likes = Column(Integer, default=0)     # 总点赞数
    total_favorites = Column(Integer, default=0) # 总收藏次数
    avg_reads = Column(Float, default=0)         # 平均阅读次数

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_wechat_account_stats_account_date', 'account_id', 'stat_date', unique=True),
    )


class WechatArticle(Base):
    """微信公众号文章基本信息（静态，不随时间变化）"""
    __tablename__ = "geo_wechat_article"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    title = Column(String(300), default="")       # 文章标题
    article_url = Column(String(500), default="")  # 文章URL
    cover_url = Column(String(500), default="")    # 封面图URL
    author = Column(String(100), default="")        # 作者
    digest = Column(String(500), default="")        # 摘要
    publish_date = Column(Date, nullable=True, index=True)  # 发布日期
    media_id = Column(String(100), default="")      # 微信素材media_id

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WechatArticleStats(Base):
    """微信公众号文章数据快照（发布后1/3/7/30天各一条）"""
    __tablename__ = "geo_wechat_article_stats"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("geo_wechat_article.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    snapshot_day = Column(Integer, default=0)  # 快照时间点：1/3/7/30（发布后第N天）
    stat_date = Column(Date, nullable=False, index=True)  # 统计日期

    # 文章数据
    int_page_read_count = Column(Integer, default=0)     # 图文页阅读次数
    int_page_read_user = Column(Integer, default=0)      # 图文页阅读人数
    ori_page_read_user = Column(Integer, default=0)      # 原文页阅读人数
    ori_page_read_count = Column(Integer, default=0)     # 原文页阅读次数
    share_user = Column(Integer, default=0)               # 分享人数
    share_count = Column(Integer, default=0)              # 分享次数
    add_to_fav_user = Column(Integer, default=0)          # 收藏人数
    add_to_fav_count = Column(Integer, default=0)         # 收藏次数
    like_count = Column(Integer, default=0)                # 点赞数
    comment_count = Column(Integer, default=0)             # 评论数

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_wechat_article_stats_article_day', 'article_id', 'snapshot_day', unique=True),
    )
```

---

### 步骤2：注册新模型

**文件**：`backend/app/models/__init__.py`

在文件末尾添加：
```python
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats
```

---

### 步骤3：数据库迁移脚本

**文件**：`backend/migrations/add_wechat_stats_tables.py`

```python
"""创建微信公众号数据统计表
运行方式：cd backend && C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.add_wechat_stats_tables
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats

def upgrade():
    print("创建微信公众号数据统计表...")
    # 创建所有表（已存在的表不会重复创建）
    Base.metadata.create_all(bind=engine, tables=[
        WechatAccountStats.__table__,
        WechatArticle.__table__,
        WechatArticleStats.__table__,
    ])
    print("✅ 表创建完成")
    print("  - geo_wechat_account_stats (账号每日统计)")
    print("  - geo_wechat_article (文章基本信息)")
    print("  - geo_wechat_article_stats (文章数据快照)")

if __name__ == "__main__":
    upgrade()
```

**执行迁移**：
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m migrations.add_wechat_stats_tables
```

---

### 步骤4：新建微信数据采集服务

**文件**：`backend/app/services/wechat_data_service.py`

```python
"""微信公众号数据采集服务
通过微信官方API采集账号数据（粉丝/文章/阅读量）。

API文档：
- 用户增减: https://developers.weixin.qq.com/doc/offiaccount/Analytics/User_Analysis_Data.html
- 图文分析: https://developers.weixin.qq.com/doc/offiaccount/Analytics/Graphic_Analysis_Data.html
"""
import logging
import requests
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.publish_account import PublishAccount
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats
from app.utils.crypto import decrypt

logger = logging.getLogger(__name__)

WECHAT_API_BASE = "https://api.weixin.qq.com"


class WechatDataService:
    """微信公众号数据采集服务"""

    @staticmethod
    def get_access_token(app_id: str, app_secret: str) -> str:
        """获取access_token"""
        url = f"{WECHAT_API_BASE}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "access_token" not in data:
            raise ValueError(f"获取access_token失败: {data}")
        return data["access_token"]

    @staticmethod
    def verify_credentials(app_id: str, app_secret: str) -> tuple[bool, str]:
        """验证AppID/AppSecret是否有效
        Returns: (is_valid, error_message)
        """
        try:
            WechatDataService.get_access_token(app_id, app_secret)
            return True, ""
        except Exception as e:
            return False, str(e)

    @staticmethod
    def collect_user_stats(access_token: str, start_date: date, end_date: date) -> list[dict]:
        """采集用户增减数据
        API: /datacube/getusersummary
        Returns: [{ref_date, user_source, new_user, cancel_user}, ...]
        """
        url = f"{WECHAT_API_BASE}/datacube/getusersummary"
        params = {"access_token": access_token}
        payload = {
            "begin_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if "list" not in data:
            logger.warning(f"获取用户增减数据失败: {data}")
            return []
        return data["list"]

    @staticmethod
    def collect_user_cumulate(access_token: str, start_date: date, end_date: date) -> list[dict]:
        """采集累计用户数据
        API: /datacube/getusercumulate
        Returns: [{ref_date, cumulate_user}, ...]
        """
        url = f"{WECHAT_API_BASE}/datacube/getusercumulate"
        params = {"access_token": access_token}
        payload = {
            "begin_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if "list" not in data:
            logger.warning(f"获取累计用户数据失败: {data}")
            return []
        return data["list"]

    @staticmethod
    def collect_article_summary(access_token: str, start_date: date, end_date: date) -> list[dict]:
        """采集图文群发每日数据
        API: /datacube/getarticlesummary
        Returns: [{ref_date, msgid, title, int_page_read_count, ...}, ...]
        """
        url = f"{WECHAT_API_BASE}/datacube/getarticlesummary"
        params = {"access_token": access_token}
        payload = {
            "begin_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if "list" not in data:
            logger.warning(f"获取图文每日数据失败: {data}")
            return []
        return data["list"]

    @staticmethod
    def collect_article_total(access_token: str, start_date: date, end_date: date) -> list[dict]:
        """采集图文群发总数据
        API: /datacube/getarticletotal
        Returns: [{ref_date, msgid, title, details: [{stat_date, int_page_read_count, ...}]}, ...]
        """
        url = f"{WECHAT_API_BASE}/datacube/getarticletotal"
        params = {"access_token": access_token}
        payload = {
            "begin_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if "list" not in data:
            logger.warning(f"获取图文总数据失败: {data}")
            return []
        return data["list"]

    @staticmethod
    def collect_material_list(access_token: str, offset: int = 0, count: int = 20) -> dict:
        """获取永久图文素材列表
        API: /material/batchget_material
        """
        url = f"{WECHAT_API_BASE}/cgi-bin/material/batchget_material"
        params = {"access_token": access_token}
        payload = {
            "type": "news",
            "offset": offset,
            "count": count,
        }
        resp = requests.post(url, params=params, json=payload, timeout=30)
        return resp.json()

    @classmethod
    def collect_and_store(cls, db: Session, account: PublishAccount, days: int = 7) -> dict:
        """采集最近N天的数据并存储到数据库

        Args:
            db: 数据库会话
            account: 发布账号
            days: 采集最近N天

        Returns: {account_stats_count, article_count, article_stats_count}
        """
        app_id = account.app_id
        app_secret = decrypt(account.app_secret) if account.app_secret else ""

        if not app_id or not app_secret:
            raise ValueError("账号未配置AppID和AppSecret")

        # 1. 获取access_token
        logger.info(f"[微信数据采集] 账号={account.account_name}，获取access_token")
        access_token = cls.get_access_token(app_id, app_secret)

        end_date = date.today() - timedelta(days=1)  # 昨天（今天的数据还没统计完）
        start_date = end_date - timedelta(days=days - 1)

        # 2. 采集用户数据
        logger.info(f"[微信数据采集] 采集用户数据 {start_date} ~ {end_date}")
        user_summary = cls.collect_user_summary(access_token, start_date, end_date)
        user_cumulate = cls.collect_user_cumulate(access_token, start_date, end_date)

        # 按日期汇总用户数据
        user_data_by_date = {}
        for item in user_summary:
            d = item.get("ref_date", "")
            if d not in user_data_by_date:
                user_data_by_date[d] = {"new_user": 0, "cancel_user": 0}
            user_data_by_date[d]["new_user"] += item.get("new_user", 0)
            user_data_by_date[d]["cancel_user"] += item.get("cancel_user", 0)

        cumulate_by_date = {}
        for item in user_cumulate:
            d = item.get("ref_date", "")
            cumulate_by_date[d] = item.get("cumulate_user", 0)

        # 3. 采集图文数据
        logger.info(f"[微信数据采集] 采集图文数据 {start_date} ~ {end_date}")
        article_summary = cls.collect_article_summary(access_token, start_date, end_date)
        article_total = cls.collect_article_total(access_token, start_date, end_date)

        # 按日期汇总图文数据
        article_data_by_date = {}
        article_info_by_msgid = {}
        for item in article_summary:
            d = item.get("ref_date", "")
            msgid = item.get("msgid", "")
            if d not in article_data_by_date:
                article_data_by_date[d] = {
                    "total_articles": 0, "total_reads": 0, "total_read_users": 0,
                    "total_shares": 0, "total_likes": 0, "total_favorites": 0,
                }
            article_data_by_date[d]["total_articles"] += 1
            article_data_by_date[d]["total_reads"] += item.get("int_page_read_count", 0)
            article_data_by_date[d]["total_read_users"] += item.get("int_page_read_user", 0)
            article_data_by_date[d]["total_shares"] += item.get("share_count", 0)
            article_data_by_date[d]["total_likes"] += item.get("like_count", 0)
            article_data_by_date[d]["total_favorites"] += item.get("add_to_fav_count", 0)

            # 记录文章基本信息
            if msgid and msgid not in article_info_by_msgid:
                article_info_by_msgid[msgid] = {
                    "title": item.get("title", ""),
                    "publish_date": d,
                }

        # 4. 存储账号每日统计
        account_stats_count = 0
        for i in range(days):
            stat_date = start_date + timedelta(days=i)
            date_str = stat_date.strftime("%Y-%m-%d")

            user_data = user_data_by_date.get(date_str, {"new_user": 0, "cancel_user": 0})
            cumulate = cumulate_by_date.get(date_str, 0)
            article_data = article_data_by_date.get(date_str, {
                "total_articles": 0, "total_reads": 0, "total_read_users": 0,
                "total_shares": 0, "total_likes": 0, "total_favorites": 0,
            })

            # 检查是否已存在
            existing = db.query(WechatAccountStats).filter(
                WechatAccountStats.account_id == account.id,
                WechatAccountStats.stat_date == stat_date,
            ).first()

            avg_reads = (article_data["total_reads"] / article_data["total_articles"]
                         if article_data["total_articles"] > 0 else 0)

            if existing:
                existing.new_users = user_data["new_user"]
                existing.cancel_users = user_data["cancel_user"]
                existing.net_growth = user_data["new_user"] - user_data["cancel_user"]
                existing.cumulate_users = cumulate
                existing.total_articles = article_data["total_articles"]
                existing.total_reads = article_data["total_reads"]
                existing.total_read_users = article_data["total_read_users"]
                existing.total_shares = article_data["total_shares"]
                existing.total_likes = article_data["total_likes"]
                existing.total_favorites = article_data["total_favorites"]
                existing.avg_reads = avg_reads
            else:
                stats = WechatAccountStats(
                    account_id=account.id,
                    user_id=account.user_id,
                    stat_date=stat_date,
                    new_users=user_data["new_user"],
                    cancel_users=user_data["cancel_user"],
                    net_growth=user_data["new_user"] - user_data["cancel_user"],
                    cumulate_users=cumulate,
                    total_articles=article_data["total_articles"],
                    total_reads=article_data["total_reads"],
                    total_read_users=article_data["total_read_users"],
                    total_shares=article_data["total_shares"],
                    total_likes=article_data["total_likes"],
                    total_favorites=article_data["total_favorites"],
                    avg_reads=avg_reads,
                )
                db.add(stats)
            account_stats_count += 1

        # 5. 存储文章基本信息和数据快照（从article_total获取更详细的数据）
        article_count = 0
        article_stats_count = 0
        for item in article_total:
            msgid = str(item.get("msgid", ""))
            title = item.get("title", "")
            details = item.get("details", [])

            if not msgid or not details:
                continue

            # 查找或创建文章记录
            article = db.query(WechatArticle).filter(
                WechatArticle.account_id == account.id,
                WechatArticle.media_id == msgid,
            ).first()

            if not article:
                # 从第一条detail获取发布日期
                first_detail = details[0] if details else {}
                publish_date_str = first_detail.get("stat_date", "")
                try:
                    publish_date = date.fromisoformat(publish_date_str) if publish_date_str else None
                except ValueError:
                    publish_date = None

                article = WechatArticle(
                    account_id=account.id,
                    user_id=account.user_id,
                    title=title,
                    media_id=msgid,
                    publish_date=publish_date,
                )
                db.add(article)
                db.flush()  # 获取article.id
                article_count += 1

            # 存储文章数据快照（取最新的一条detail作为当前快照）
            # 简化处理：每条article_total的最新detail存为snapshot_day=0（当前数据）
            # 完整的1/3/7/30天快照逻辑在阶段四B实现
            if details:
                latest = details[-1]
                stat_date_str = latest.get("stat_date", "")
                try:
                    stat_date = date.fromisoformat(stat_date_str) if stat_date_str else date.today()
                except ValueError:
                    stat_date = date.today()

                existing_stats = db.query(WechatArticleStats).filter(
                    WechatArticleStats.article_id == article.id,
                    WechatArticleStats.snapshot_day == 0,
                ).first()

                if existing_stats:
                    existing_stats.stat_date = stat_date
                    existing_stats.int_page_read_count = latest.get("int_page_read_count", 0)
                    existing_stats.int_page_read_user = latest.get("int_page_read_user", 0)
                    existing_stats.ori_page_read_user = latest.get("ori_page_read_user", 0)
                    existing_stats.ori_page_read_count = latest.get("ori_page_read_count", 0)
                    existing_stats.share_user = latest.get("share_user", 0)
                    existing_stats.share_count = latest.get("share_count", 0)
                    existing_stats.add_to_fav_user = latest.get("add_to_fav_user", 0)
                    existing_stats.add_to_fav_count = latest.get("add_to_fav_count", 0)
                    existing_stats.like_count = latest.get("like_count", 0)
                else:
                    stats = WechatArticleStats(
                        article_id=article.id,
                        account_id=account.id,
                        user_id=account.user_id,
                        snapshot_day=0,
                        stat_date=stat_date,
                        int_page_read_count=latest.get("int_page_read_count", 0),
                        int_page_read_user=latest.get("int_page_read_user", 0),
                        ori_page_read_user=latest.get("ori_page_read_user", 0),
                        ori_page_read_count=latest.get("ori_page_read_count", 0),
                        share_user=latest.get("share_user", 0),
                        share_count=latest.get("share_count", 0),
                        add_to_fav_user=latest.get("add_to_fav_user", 0),
                        add_to_fav_count=latest.get("add_to_fav_count", 0),
                        like_count=latest.get("like_count", 0),
                    )
                    db.add(stats)
                    article_stats_count += 1

        db.commit()

        result = {
            "account_stats_count": account_stats_count,
            "article_count": article_count,
            "article_stats_count": article_stats_count,
        }
        logger.info(f"[微信数据采集] 完成: {result}")
        return result
```

---

### 步骤5：新建数据采集异步任务

**文件**：`backend/app/worker/wechat_data_tasks.py`

```python
"""微信公众号数据采集异步任务"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.publish_account import PublishAccount
from app.services.wechat_data_service import WechatDataService
from app.worker.task_registry import register_handler

logger = logging.getLogger(__name__)


def handle_wechat_data_collect(db: Session, task: AsyncTask, on_progress) -> dict:
    """处理微信公众号数据采集任务

    payload: {account_id: int, days: int}
    """
    payload = json.loads(task.payload_json or "{}")
    account_id = payload.get("account_id")
    days = payload.get("days", 7)

    if not account_id:
        raise ValueError("缺少account_id参数")

    account = db.query(PublishAccount).filter(PublishAccount.id == account_id).first()
    if not account:
        raise ValueError(f"账号不存在: {account_id}")

    on_progress(1, 3, f"开始采集账号 [{account.account_name}] 数据")

    result = WechatDataService.collect_and_store(db, account, days=days)

    on_progress(3, 3, f"采集完成: 账号统计{result['account_stats_count']}天, "
                       f"文章{result['article_count']}篇, 文章数据{result['article_stats_count']}条")

    return result


# 注册任务处理函数
register_handler("wechat_data_collect", handle_wechat_data_collect)
```

---

### 步骤6：注册新任务类型到Worker

**文件**：`backend/app/worker/worker.py`

**修改1**：第38行后添加导入（精确到行）：
```python
import app.worker.wechat_data_tasks  # noqa: F401
```

**修改2**：在 `TASK_TIMEOUT_BY_TYPE` 字典（第59-67行）中添加：
```python
"wechat_data_collect": 300,  # 微信数据采集：5分钟
```

---

### 步骤7：新增定时采集任务

**文件**：`backend/app/main.py`

**修改1**：在 `scheduled_collect` 函数后（约第119行后）添加新函数：

```python
def scheduled_collect_wechat_data():
    """定时采集微信公众号数据：每天凌晨2点自动采集所有已验证账号的前一天数据"""
    try:
        import json
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
                    payload_json=json.dumps({"account_id": account.id, "days": 1}, ensure_ascii=False),
                    progress_message=f"定时采集微信公众号数据 [{account.account_name}]",
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
```

**修改2**：在 `lifespan` 函数中，现有定时任务注册后（约第155行后）添加：

```python
        # 微信公众号数据定时采集（每天凌晨2点）
        scheduler.add_job(
            scheduled_collect_wechat_data,
            'cron',
            hour=2,
            minute=0,
            id='daily_wechat_data_collect',
            replace_existing=True
        )
        print("⏰ 微信公众号数据定时采集已启动（每天02:00自动采集）")
```

---

### 步骤8：新增数据API

**文件**：`backend/app/api/publish_account.py`

**修改1**：在文件顶部添加导入：
```python
from datetime import date, timedelta
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats
from app.services.wechat_data_service import WechatDataService
from app.models.task import AsyncTask
import json
```

**修改2**：在 `verify_account` 函数后（文件末尾）添加以下5个API：

```python
@router.post("/{account_id}/verify-real", summary="真实验证微信账号（调用API）")
def verify_account_real(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """调用微信API真实验证AppID/AppSecret是否有效"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.platform != "wechat":
        raise HTTPException(status_code=400, detail="仅支持微信公众号真实验证")

    app_secret = decrypt(account.app_secret) if account.app_secret else ""
    is_valid, error_msg = WechatDataService.verify_credentials(account.app_id, app_secret)

    if is_valid:
        account.login_status = "valid"
        account.last_verified_at = datetime.now()
        db.commit()
        return {"code": 0, "message": "验证成功", "data": {"valid": True}}
    else:
        account.login_status = "expired"
        account.last_verified_at = datetime.now()
        db.commit()
        return {"code": 0, "message": "验证失败", "data": {"valid": False, "error": error_msg}}


@router.get("/{account_id}/stats/overview", summary="账号数据概览")
def get_account_stats_overview(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取账号数据概览（最新数据+汇总）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 获取最近30天的统计数据
    start_date = date.today() - timedelta(days=30)
    stats_list = db.query(WechatAccountStats).filter(
        WechatAccountStats.account_id == account_id,
        WechatAccountStats.stat_date >= start_date,
    ).order_by(WechatAccountStats.stat_date.desc()).all()

    if not stats_list:
        return {"code": 0, "message": "success", "data": {
            "has_data": False,
            "message": "暂无数据，请先点击'手动采集'获取数据"
        }}

    latest = stats_list[0]

    # 计算30天汇总
    total_new_users = sum(s.new_users for s in stats_list)
    total_cancel_users = sum(s.cancel_users for s in stats_list)
    total_articles = sum(s.total_articles for s in stats_list)
    total_reads = sum(s.total_reads for s in stats_list)
    total_shares = sum(s.total_shares for s in stats_list)
    total_likes = sum(s.total_likes for s in stats_list)
    avg_reads_30d = (total_reads / total_articles) if total_articles > 0 else 0

    # 获取文章总数
    article_count = db.query(WechatArticle).filter(
        WechatArticle.account_id == account_id
    ).count()

    return {"code": 0, "message": "success", "data": {
        "has_data": True,
        "latest_date": latest.stat_date.isoformat(),
        "cumulate_users": latest.cumulate_users,
        "today_new_users": latest.new_users,
        "today_cancel_users": latest.cancel_users,
        "today_net_growth": latest.net_growth,
        "today_articles": latest.total_articles,
        "today_reads": latest.total_reads,
        "today_avg_reads": latest.avg_reads,
        # 30天汇总
        "month_new_users": total_new_users,
        "month_cancel_users": total_cancel_users,
        "month_net_growth": total_new_users - total_cancel_users,
        "month_articles": total_articles,
        "month_reads": total_reads,
        "month_shares": total_shares,
        "month_likes": total_likes,
        "month_avg_reads": avg_reads_30d,
        "total_articles": article_count,
    }}


@router.get("/{account_id}/stats/trend", summary="账号数据趋势")
def get_account_stats_trend(
    account_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取账号数据趋势（按日期）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    days = min(max(days, 7), 90)  # 限制7-90天
    start_date = date.today() - timedelta(days=days)

    stats_list = db.query(WechatAccountStats).filter(
        WechatAccountStats.account_id == account_id,
        WechatAccountStats.stat_date >= start_date,
    ).order_by(WechatAccountStats.stat_date.asc()).all()

    dates = [s.stat_date.isoformat() for s in stats_list]
    cumulate_users = [s.cumulate_users for s in stats_list]
    new_users = [s.new_users for s in stats_list]
    net_growth = [s.net_growth for s in stats_list]
    total_reads = [s.total_reads for s in stats_list]
    total_articles = [s.total_articles for s in stats_list]
    avg_reads = [s.avg_reads for s in stats_list]

    return {"code": 0, "message": "success", "data": {
        "dates": dates,
        "cumulate_users": cumulate_users,
        "new_users": new_users,
        "net_growth": net_growth,
        "total_reads": total_reads,
        "total_articles": total_articles,
        "avg_reads": avg_reads,
    }}


@router.get("/{account_id}/articles", summary="账号文章列表")
def get_account_articles(
    account_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取账号已发布文章列表（含最新数据）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    query = db.query(WechatArticle).filter(WechatArticle.account_id == account_id)
    total = query.count()
    articles = query.order_by(WechatArticle.publish_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    for article in articles:
        # 获取最新的文章数据快照
        latest_stats = db.query(WechatArticleStats).filter(
            WechatArticleStats.article_id == article.id
        ).order_by(WechatArticleStats.stat_date.desc()).first()

        items.append({
            "id": article.id,
            "title": article.title,
            "article_url": article.article_url,
            "publish_date": article.publish_date.isoformat() if article.publish_date else None,
            "reads": latest_stats.int_page_read_count if latest_stats else 0,
            "read_users": latest_stats.int_page_read_user if latest_stats else 0,
            "shares": latest_stats.share_count if latest_stats else 0,
            "likes": latest_stats.like_count if latest_stats else 0,
            "favorites": latest_stats.add_to_fav_count if latest_stats else 0,
        })

    return {"code": 0, "message": "success", "data": {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }}


@router.post("/{account_id}/stats/collect", summary="手动触发数据采集")
def collect_account_stats(
    account_id: int,
    days: int = 7,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """手动触发微信公众号数据采集（异步任务）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.platform != "wechat":
        raise HTTPException(status_code=400, detail="仅支持微信公众号数据采集")

    if account.login_status != "valid":
        raise HTTPException(status_code=400, detail="账号未验证，请先验证账号")

    # 检查是否已有running/queued的采集任务
    existing = db.query(AsyncTask).filter(
        AsyncTask.task_type == "wechat_data_collect",
        AsyncTask.status.in_(["queued", "running"]),
        AsyncTask.created_by == user_id,
    ).first()
    if existing:
        return {"code": 0, "message": "已有采集任务在执行中，请稍候", "data": {"task_id": existing.id}}

    days = min(max(days, 1), 90)  # 限制1-90天

    task = AsyncTask(
        task_type="wechat_data_collect",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({"account_id": account.id, "days": days}, ensure_ascii=False),
        progress_message=f"手动采集微信公众号数据 [{account.account_name}]，最近{days}天",
    )
    db.add(task)
    db.commit()

    return {"code": 0, "message": "采集任务已提交", "data": {"task_id": task.id}}
```

---

### 步骤9：完善微信发布器

**文件**：`backend/app/publishers/wechat.py`

**修改1**：在 `_upload_news` 方法前添加封面图上传方法：

```python
    def _upload_image(self, access_token: str, image_url: str = "", image_data: bytes = None) -> str:
        """上传封面图，返回thumb_media_id
        支持传入图片URL或图片二进制数据
        """
        import tempfile
        import os

        url = f"{WECHAT_API_BASE}/cgi-bin/material/add_material"
        params = {"access_token": access_token, "type": "image"}

        try:
            if image_data:
                # 使用传入的二进制数据
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    f.write(image_data)
                    temp_path = f.name
            elif image_url:
                # 下载图片
                resp = requests.get(image_url, timeout=30)
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    f.write(resp.content)
                    temp_path = f.name
            else:
                return ""  # 没有图片，返回空（用默认封面）

            with open(temp_path, "rb") as f:
                files = {"media": f}
                resp = requests.post(url, params=params, files=files, timeout=30)

            data = resp.json()
            if "media_id" not in data:
                logger.warning(f"上传封面图失败: {data}")
                return ""
            return data["media_id"]
        except Exception as e:
            logger.error(f"上传封面图异常: {e}")
            return ""
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
```

**修改2**：修改 `_upload_news` 方法，支持封面图参数：

在方法签名中添加 `cover_url: str = ""` 参数：
```python
    def _upload_news(self, access_token: str, title: str, content: str,
                     author: str = "", digest: str = "", cover_url: str = "") -> str:
```

在方法体内，上传图文素材前先上传封面图：
```python
        # 上传封面图
        thumb_media_id = self._upload_image(access_token, image_url=cover_url)
```

将原来的 `"thumb_media_id": ""` 改为 `"thumb_media_id": thumb_media_id`。

**修改3**：修改 `publish` 方法，支持封面图参数，并在发布后轮询获取真实URL：

在方法签名中添加 `cover_url: str = ""` 参数：
```python
    def publish(self, title: str, content: str, account: dict, **kwargs) -> PublishResult:
```

在方法体内获取cover_url：
```python
            cover_url = kwargs.get("cover_url", "")
```

修改 `_upload_news` 调用，传入cover_url：
```python
            media_id = self._upload_news(access_token, title, content, author, digest, cover_url)
```

在发布成功后，添加轮询获取真实文章URL的逻辑（在 `return PublishResult` 前）：

```python
            # 轮询查询发布状态，获取真实文章URL（最多轮询5次，每次间隔3秒）
            article_url = ""
            for attempt in range(5):
                import time
                time.sleep(3)
                status_data = self._get_publish_status(access_token, publish_id)
                publish_status = status_data.get("publish_status", -1)
                if publish_status == 0:
                    # 发布成功，获取文章URL
                    article_detail = status_data.get("article_detail", [])
                    if article_detail:
                        article_url = article_detail[0].get("url", "")
                    break
                elif publish_status == 2:
                    # 发布失败
                    break
                # publish_status=1(发布中)或3(原创审核中)，继续等待
```

将原来的 `article_url = ""` 删除（因为上面已经定义了）。

---

### 步骤10：新建前端账号数据概览页面

**文件**：`frontend/src/pages/WechatAccountStats.tsx`

```tsx
import { useState, useEffect } from 'react'
import {
  Card, Row, Col, Statistic, Button, Table, Tag, message,
  DatePicker, Space, Spin, Empty, Alert
} from 'antd'
import {
  ReloadOutlined, ArrowUpOutlined, ArrowDownOutlined,
  FileTextOutlined, EyeOutlined, LikeOutlined, ShareAltOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request from '@/api'
import { useParams, useNavigate } from 'react-router-dom'

const WechatAccountStats = () => {
  const { accountId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [collecting, setCollecting] = useState(false)
  const [overview, setOverview] = useState<any>(null)
  const [trendData, setTrendData] = useState<any>(null)
  const [articles, setArticles] = useState<any[]>([])
  const [articlesTotal, setArticlesTotal] = useState(0)
  const [articlesPage, setArticlesPage] = useState(1)
  const [trendDays, setTrendDays] = useState(30)

  const loadOverview = async () => {
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/stats/overview`)
      setOverview(res.data?.data)
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const loadTrend = async (days = 30) => {
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/stats/trend`, {
        params: { days }
      })
      setTrendData(res.data?.data)
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const loadArticles = async (page = 1) => {
    setLoading(true)
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/articles`, {
        params: { page, page_size: 10 }
      })
      setArticles(res.data?.data?.items || [])
      setArticlesTotal(res.data?.data?.total || 0)
      setArticlesPage(page)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }

  const handleCollect = async () => {
    setCollecting(true)
    try {
      const res: any = await request.post(`/publish-accounts/${accountId}/stats/collect`, null, {
        params: { days: 7 }
      })
      message.success('采集任务已提交，约1-2分钟后完成')
      // 5秒后开始轮询刷新
      setTimeout(() => {
        loadOverview()
        loadTrend(trendDays)
        loadArticles(1)
      }, 5000)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setCollecting(false)
    }
  }

  useEffect(() => {
    if (accountId) {
      loadOverview()
      loadTrend(30)
      loadArticles(1)
    }
  }, [accountId])

  // 粉丝趋势图配置
  const fanTrendOption = trendData ? {
    title: { text: '粉丝数趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['累计粉丝', '新增粉丝', '净增'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: trendData.dates, axisLabel: { rotate: 45 } },
    yAxis: [
      { type: 'value', name: '累计粉丝' },
      { type: 'value', name: '新增/净增' }
    ],
    series: [
      { name: '累计粉丝', type: 'line', data: trendData.cumulate_users, smooth: true, yAxisIndex: 0 },
      { name: '新增粉丝', type: 'bar', data: trendData.new_users, yAxisIndex: 1 },
      { name: '净增', type: 'line', data: trendData.net_growth, smooth: true, yAxisIndex: 1 },
    ]
  } : {}

  // 阅读趋势图配置
  const readTrendOption = trendData ? {
    title: { text: '文章阅读趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['总阅读量', '发文数', '平均阅读'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: trendData.dates, axisLabel: { rotate: 45 } },
    yAxis: [
      { type: 'value', name: '阅读量' },
      { type: 'value', name: '发文数' }
    ],
    series: [
      { name: '总阅读量', type: 'line', data: trendData.total_reads, smooth: true, areaStyle: {}, yAxisIndex: 0 },
      { name: '发文数', type: 'bar', data: trendData.total_articles, yAxisIndex: 1 },
      { name: '平均阅读', type: 'line', data: trendData.avg_reads, smooth: true, yAxisIndex: 0 },
    ]
  } : {}

  const articleColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: '30%' },
    { title: '发布日期', dataIndex: 'publish_date', key: 'publish_date', width: 100 },
    { title: '阅读量', dataIndex: 'reads', key: 'reads', width: 80, render: (v: number) => <span><EyeOutlined /> {v}</span> },
    { title: '点赞', dataIndex: 'likes', key: 'likes', width: 70, render: (v: number) => <span><LikeOutlined /> {v}</span> },
    { title: '分享', dataIndex: 'shares', key: 'shares', width: 70, render: (v: number) => <span><ShareAltOutlined /> {v}</span> },
    { title: '收藏', dataIndex: 'favorites', key: 'favorites', width: 70 },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={() => navigate(-1)}>返回</Button>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={collecting}
          onClick={handleCollect}
        >
          手动采集数据（最近7天）
        </Button>
      </Space>

      {overview && !overview.has_data ? (
        <Empty description={overview.message || '暂无数据'}>
          <Button type="primary" onClick={handleCollect}>立即采集</Button>
        </Empty>
      ) : (
        <>
          {/* 数据概览卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="累计粉丝" value={overview?.cumulate_users || 0} />
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  {overview?.today_net_growth >= 0 ? (
                    <Tag color="green"><ArrowUpOutlined /> 今日+{overview?.today_net_growth}</Tag>
                  ) : (
                    <Tag color="red"><ArrowDownOutlined /> 今日{overview?.today_net_growth}</Tag>
                  )}
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="今日发文" value={overview?.today_articles || 0} prefix={<FileTextOutlined />} />
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  本月共 {overview?.month_articles || 0} 篇
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="今日阅读量" value={overview?.today_reads || 0} prefix={<EyeOutlined />} />
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  平均阅读 {overview?.today_avg_reads?.toFixed(0) || 0}
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="本月总阅读" value={overview?.month_reads || 0} prefix={<EyeOutlined />} />
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  平均阅读 {overview?.month_avg_reads?.toFixed(0) || 0}
                </div>
              </Card>
            </Col>
          </Row>

          {/* 30天汇总 */}
          <Card title="近30天汇总" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={4}><Statistic title="新增粉丝" value={overview?.month_new_users || 0} /></Col>
              <Col span={4}><Statistic title="取关" value={overview?.month_cancel_users || 0} /></Col>
              <Col span={4}><Statistic title="净增" value={overview?.month_net_growth || 0} /></Col>
              <Col span={4}><Statistic title="发文数" value={overview?.month_articles || 0} /></Col>
              <Col span={4}><Statistic title="总分享" value={overview?.month_shares || 0} /></Col>
              <Col span={4}><Statistic title="总点赞" value={overview?.month_likes || 0} /></Col>
            </Row>
          </Card>

          {/* 趋势图 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card
                title="粉丝趋势"
                extra={
                  <Select value={trendDays} onChange={(v) => { setTrendDays(v); loadTrend(v) }} style={{ width: 100 }}>
                    <Select.Option value={7}>近7天</Select.Option>
                    <Select.Option value={30}>近30天</Select.Option>
                    <Select.Option value={90}>近90天</Select.Option>
                  </Select>
                }
              >
                <ReactECharts option={fanTrendOption} style={{ height: 300 }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="阅读趋势">
                <ReactECharts option={readTrendOption} style={{ height: 300 }} />
              </Card>
            </Col>
          </Row>

          {/* 文章列表 */}
          <Card title="已发布文章">
            <Table
              columns={articleColumns}
              dataSource={articles}
              rowKey="id"
              loading={loading}
              pagination={{
                current: articlesPage,
                pageSize: 10,
                total: articlesTotal,
                onChange: (page) => loadArticles(page),
              }}
            />
          </Card>
        </>
      )}
    </div>
  )
}

export default WechatAccountStats
```

---

### 步骤11：注册前端路由

**文件**：`frontend/src/App.tsx`

在路由配置中添加：
```tsx
<Route path="/publish-accounts/:accountId/stats" element={<WechatAccountStats />} />
```

并在文件顶部添加导入：
```tsx
import WechatAccountStats from './pages/WechatAccountStats'
```

---

### 步骤12：修改发布账号列表页，增加"查看数据"按钮

**文件**：`frontend/src/pages/PublishAccounts.tsx`

**修改1**：在文件顶部添加导入：
```tsx
import { useNavigate } from 'react-router-dom'
import { BarChartOutlined } from '@ant-design/icons'
```

**修改2**：在组件内添加navigate：
```tsx
const navigate = useNavigate()
```

**修改3**：在表格columns中添加"操作"列（如果已有操作列，在其中增加按钮）：

在 `STATUS_MAP` 后添加columns定义（如果文件中没有columns，需要添加）：
```tsx
const columns = [
  { title: '平台', dataIndex: 'platform', key: 'platform', render: (p: string) => PUBLISH_PLATFORM_NAMES[p] || p },
  { title: '账号名称', dataIndex: 'account_name', key: 'account_name' },
  { title: '状态', dataIndex: 'login_status', key: 'login_status', render: (s: string) => {
      const info = STATUS_MAP[s] || STATUS_MAP.unknown
      return <Tag color={info.color}>{info.label}</Tag>
    }
  },
  { title: '最后验证', dataIndex: 'last_verified_at', key: 'last_verified_at', render: (t: string) => t ? new Date(t).toLocaleDateString() : '-' },
  {
    title: '操作', key: 'action', render: (_: any, record: PublishAccount) => (
      <Space>
        {record.platform === 'wechat' && (
          <Button type="link" icon={<BarChartOutlined />} onClick={() => navigate(`/publish-accounts/${record.id}/stats`)}>
            数据
          </Button>
        )}
        <Button type="link" onClick={() => handleVerify(record.id)}>验证</Button>
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger>删除</Button>
        </Popconfirm>
      </Space>
    )
  },
]
```

**修改4**：将原来的Table组件改为使用columns：
```tsx
<Table columns={columns} dataSource={list} rowKey="id" loading={loading} />
```

如果原来的Table有自定义的列定义，需要替换为上面的columns。

---

### 步骤13：修改"验证"按钮为真实验证

**文件**：`frontend/src/pages/PublishAccounts.tsx`

修改 `handleVerify` 函数，微信公众号调用真实验证API：

```tsx
const handleVerify = async (id: number, platform: string) => {
  try {
    if (platform === 'wechat') {
      // 微信公众号调用真实验证API
      const res: any = await request.post(`/publish-accounts/${id}/verify-real`)
      if (res.data?.data?.valid) {
        message.success('验证成功')
      } else {
        message.error(`验证失败: ${res.data?.data?.error || 'AppID或AppSecret无效'}`)
      }
    } else {
      // 其他平台手动标记
      await request.post(`/publish-accounts/${id}/verify`)
      message.success('已标记为有效')
    }
    loadList()
  } catch (e) {
    // 错误已由拦截器处理
  }
}
```

同时修改columns中验证按钮的onClick，传入platform：
```tsx
<Button type="link" onClick={() => handleVerify(record.id, record.platform)}>验证</Button>
```

---

## 四、验证清单

### 后端验证

1. **数据库迁移**：
   ```bash
   cd C:\Users\jenac\Desktop\GEO\backend
   C:\Users\jenac\miniconda3\python.exe -m migrations.add_wechat_stats_tables
   ```
   确认3张表创建成功。

2. **后端import检查**：
   ```bash
   C:\Users\jenac\miniconda3\python.exe -c "from app.main import app; print('import OK')"
   ```

3. **后端启动**：启动后端，确认无ERROR，定时任务注册成功。

4. **API测试**（用Postman或curl）：
   - `POST /api/v1/publish-accounts/{id}/verify-real` — 真实验证
   - `GET /api/v1/publish-accounts/{id}/stats/overview` — 数据概览
   - `GET /api/v1/publish-accounts/{id}/stats/trend?days=30` — 数据趋势
   - `GET /api/v1/publish-accounts/{id}/articles` — 文章列表
   - `POST /api/v1/publish-accounts/{id}/stats/collect?days=7` — 手动采集

### 前端验证

1. **前端tsc检查**：
   ```bash
   cd C:\Users\jenac\Desktop\GEO\frontend
   npx tsc --noEmit
   ```

2. **前端启动**：启动前端，确认无编译错误。

3. **页面测试**：
   - 发布账号列表页：微信公众号账号显示"数据"按钮
   - 点击"数据"按钮：进入账号数据概览页
   - 点击"手动采集数据"：提交采集任务，5秒后数据刷新
   - 验证按钮：微信公众号调用真实验证，成功/失败有明确提示
   - 趋势图：粉丝趋势图和阅读趋势图正常渲染
   - 文章列表：已发布文章列表显示，含阅读量/点赞/分享

### 发布器验证

1. 发布一篇文章到微信公众号，确认：
   - 封面图正常上传（如果传入了cover_url）
   - 发布后能获取到真实的文章URL
   - 发布状态正确（published/reviewing/failed）

---

## 五、注意事项

1. **微信API权限**：数据统计API需要认证的服务号才能调用。用户已确认"层次智慧"是服务号，但其他用户添加的账号可能是订阅号，订阅号可能没有数据API权限。采集时如果API返回权限错误，要记录日志并给用户提示。

2. **API调用频率限制**：每个access_token每天有2000次调用限制。50用户×每个用户1-2个账号×每天采集一次（约10次API调用/账号）= 每天约1000次，在限制内。但手动采集时要注意不要频繁触发。

3. **数据延迟**：微信公众号的数据统计API有1天延迟，今天的数据要明天才能获取。所以定时采集在凌晨2点执行，采集前一天的数据。

4. **app_secret加密存储**：PublishAccount模型中app_secret是加密存储的，采集时需要用decrypt解密。

5. **用户隔离**：所有API都要校验user_id，确保用户只能查看自己的账号数据。

6. **文章URL获取**：微信发布是异步的，发布后需要轮询查询状态才能获取真实URL。最多轮询5次，每次间隔3秒。如果5次后还没发布成功，返回空URL，后续可以通过check_status查询。

---

## 六、Git提交

完成所有改动并验证通过后：

```bash
cd C:\Users\jenac\Desktop\GEO
git add backend/app/models/wechat_stats.py
git add backend/app/models/__init__.py
git add backend/app/services/wechat_data_service.py
git add backend/app/worker/wechat_data_tasks.py
git add backend/app/worker/worker.py
git add backend/app/api/publish_account.py
git add backend/app/publishers/wechat.py
git add backend/app/main.py
git add backend/migrations/add_wechat_stats_tables.py
git add frontend/src/pages/WechatAccountStats.tsx
git add frontend/src/pages/PublishAccounts.tsx
git add frontend/src/App.tsx
git commit -m "feat: 阶段四A-微信公众号数据采集与账号概览（8项）"
```

---

**手册结束。有任何不明白的地方，在执行过程中主动提出讨论。**
