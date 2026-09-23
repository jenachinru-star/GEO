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
        user_summary = cls.collect_user_stats(access_token, start_date, end_date)
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
