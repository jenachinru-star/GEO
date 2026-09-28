"""对标账号数据对比服务
计算自己账号与对标账号的数据对比，用于竞品分析页面展示。
"""
import logging
from sqlalchemy.orm import Session
from app.models.publish_account import PublishAccount
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats
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
