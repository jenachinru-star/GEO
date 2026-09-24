# -*- coding: utf-8 -*-
"""微信公众号数据采集服务
通过微信官方API采集账号数据（粉丝/文章/阅读量）。

API文档：
- 用户增减: https://developers.weixin.qq.com/doc/offiaccount/Analytics/User_Analysis_Data.html
- 图文分析: https://developers.weixin.qq.com/doc/offiaccount/Analytics/Graphic_Analysis_Data.html

微信接口限制（阶段四B按官方文档修正，手册原设计有误）：
- getusersummary / getusercumulate 最大时间跨度 7 天 → 分块采集
- getarticlesummary / getarticletotal 最大时间跨度 1 天 → 逐日循环调用
- getarticletotal 的 details 中，每天的数值是"截至该日的累计总量"（非当日新增），直接读取
- getarticletotal 最多只统计发表日后 7 天数据 → 仅做 day_1/3/7，day_30 留待新接口（阶段四C）
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

# 文章快照时间点（getarticletotal 仅覆盖发表后7天，day_30 不填充）
SNAPSHOT_DAYS = [1, 3, 7]
# 用户类接口单次最大跨度（天）
USER_STATS_MAX_SPAN = 7


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
        API: /datacube/getusersummary（最大跨度7天）
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
        API: /datacube/getusercumulate（最大跨度7天）
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

    @classmethod
    def _collect_user_stats_chunked(cls, access_token: str,
                                    start_date: date, end_date: date
                                    ) -> tuple[dict, dict]:
        """分块采集用户数据（每块最多7天）

        Returns: (user_data_by_date, cumulate_by_date)
        """
        user_data_by_date: dict = {}
        cumulate_by_date: dict = {}

        cur = start_date
        while cur <= end_date:
            chunk_end = min(cur + timedelta(days=USER_STATS_MAX_SPAN - 1), end_date)

            for item in cls.collect_user_stats(access_token, cur, chunk_end):
                d = item.get("ref_date", "")
                if d not in user_data_by_date:
                    user_data_by_date[d] = {"new_user": 0, "cancel_user": 0}
                user_data_by_date[d]["new_user"] += item.get("new_user", 0)
                user_data_by_date[d]["cancel_user"] += item.get("cancel_user", 0)

            for item in cls.collect_user_cumulate(access_token, cur, chunk_end):
                d = item.get("ref_date", "")
                cumulate_by_date[d] = item.get("cumulate_user", 0)

            cur = chunk_end + timedelta(days=1)

        return user_data_by_date, cumulate_by_date

    @staticmethod
    def collect_article_summary(access_token: str, start_date: date, end_date: date) -> list[dict]:
        """采集图文群发每日数据
        API: /datacube/getarticlesummary（最大跨度1天）
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
        API: /datacube/getarticletotal（最大跨度1天）
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
    def collect_and_store(cls, db: Session, account: PublishAccount,
                          days: int = 7, ref_dates: list[date] | None = None) -> dict:
        """采集数据并存储到数据库

        Args:
            db: 数据库会话
            account: 发布账号
            days: 采集最近N天（ref_dates 为空时使用）
            ref_dates: 显式指定要查询的群发日（date列表，定时任务用）。
                        传入时账号每日统计仍覆盖 [min(ref_dates), max(ref_dates)] 连续区间。

        Returns: {account_stats_count, article_count, article_stats_count}
        """
        app_id = account.app_id
        app_secret = decrypt(account.app_secret) if account.app_secret else ""

        if not app_id or not app_secret:
            raise ValueError("账号未配置AppID和AppSecret")

        yesterday = date.today() - timedelta(days=1)

        # 解析查询日期（所有 datacube 接口 end_date 最大为昨天）
        if ref_dates:
            query_dates = sorted({d for d in ref_dates if d <= yesterday})
            if not query_dates:
                raise ValueError("没有可查询的日期（日期不能晚于昨天）")
            window_start, window_end = query_dates[0], query_dates[-1]
        else:
            window_end = yesterday
            window_start = window_end - timedelta(days=days - 1)
            query_dates = [window_start + timedelta(days=i) for i in range(days)]

        # 1. 获取access_token
        logger.info(f"[微信数据采集] 账号={account.account_name}，获取access_token")
        access_token = cls.get_access_token(app_id, app_secret)

        # 2. 采集用户数据（7天一块）
        logger.info(f"[微信数据采集] 采集用户数据 {window_start} ~ {window_end}")
        user_data_by_date, cumulate_by_date = cls._collect_user_stats_chunked(
            access_token, window_start, window_end
        )

        # 3. 采集图文数据（逐日循环，每日一次调用）
        logger.info(f"[微信数据采集] 逐日采集图文数据，共 {len(query_dates)} 天")
        article_data_by_date = {}
        article_total: list[dict] = []
        for query_date in query_dates:
            article_summary = cls.collect_article_summary(access_token, query_date, query_date)
            article_total.extend(cls.collect_article_total(access_token, query_date, query_date))

            for item in article_summary:
                d = item.get("ref_date", "")
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

        # 4. 存储账号每日统计（连续区间 window_start ~ window_end）
        account_stats_count = 0
        span_days = (window_end - window_start).days + 1
        for i in range(span_days):
            stat_date = window_start + timedelta(days=i)
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

        # 5. 存储文章基本信息和数据快照（details 为累计总量，直接读取）
        article_count = 0
        article_stats_count = 0
        for item in article_total:
            msgid = str(item.get("msgid", ""))
            title = item.get("title", "")
            details = item.get("details", [])

            if not msgid or not details:
                continue

            # 5.1 先按 msgid 查找
            article = db.query(WechatArticle).filter(
                WechatArticle.account_id == account.id,
                WechatArticle.media_id == msgid,
            ).first()

            # 5.2 兜底：同账号 + 标题完全相同（关联本系统发布时创建、带正文的记录）
            if not article and title:
                article = db.query(WechatArticle).filter(
                    WechatArticle.account_id == account.id,
                    WechatArticle.title == title,
                ).first()
                if article and not article.media_id:
                    # 回填 datacube msgid，使后续采集可直接命中
                    article.media_id = msgid

            # 从第一条 detail 解析发布日期
            first_detail = details[0] if details else {}
            publish_date_str = first_detail.get("stat_date", "")
            try:
                parsed_publish_date = date.fromisoformat(publish_date_str) if publish_date_str else None
            except ValueError:
                parsed_publish_date = None

            if not article:
                article = WechatArticle(
                    account_id=account.id,
                    user_id=account.user_id,
                    title=title,
                    media_id=msgid,
                    publish_date=parsed_publish_date,
                )
                db.add(article)
                db.flush()  # 获取article.id
                article_count += 1
            elif not article.publish_date and parsed_publish_date:
                # 补全缺失的发布日期
                article.publish_date = parsed_publish_date

            if not article.publish_date:
                continue

            # 5.3 details 行是"截至该日的累计总量"，按 stat_date 推算发布后第N天，直读
            sorted_details = sorted(details, key=lambda x: x.get("stat_date", ""))
            for detail in sorted_details:
                stat_date_str = detail.get("stat_date", "")
                try:
                    stat_date = date.fromisoformat(stat_date_str)
                except ValueError:
                    continue

                day_n = (stat_date - article.publish_date).days + 1
                if day_n in SNAPSHOT_DAYS:
                    cls._save_article_snapshot(
                        db, article, account, day_n, stat_date, detail
                    )
                    article_stats_count += 1

            # 5.4 保存最新累计数据为 snapshot_day=0（当前数据）
            latest = sorted_details[-1]
            try:
                latest_stat_date = date.fromisoformat(latest.get("stat_date", ""))
            except ValueError:
                latest_stat_date = date.today()
            cls._save_article_snapshot(
                db, article, account, 0, latest_stat_date, latest
            )

        db.commit()

        result = {
            "account_stats_count": account_stats_count,
            "article_count": article_count,
            "article_stats_count": article_stats_count,
        }
        logger.info(f"[微信数据采集] 完成: {result}")
        return result

    @staticmethod
    def _save_article_snapshot(db: Session, article: WechatArticle,
                               account: PublishAccount, snapshot_day: int,
                               stat_date: date, data: dict):
        """保存或更新文章数据快照

        Args:
            data: 微信返回的 details 行（累计总量），字段名与表列一致
        """
        value_fields = [
            "int_page_read_count", "int_page_read_user",
            "ori_page_read_user", "ori_page_read_count",
            "share_user", "share_count",
            "add_to_fav_user", "add_to_fav_count",
            "like_count",
        ]
        values = {k: data.get(k, 0) for k in value_fields}

        existing = db.query(WechatArticleStats).filter(
            WechatArticleStats.article_id == article.id,
            WechatArticleStats.snapshot_day == snapshot_day,
        ).first()

        if existing:
            existing.stat_date = stat_date
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            stats = WechatArticleStats(
                article_id=article.id,
                account_id=account.id,
                user_id=account.user_id,
                snapshot_day=snapshot_day,
                stat_date=stat_date,
                **values,
            )
            db.add(stats)
