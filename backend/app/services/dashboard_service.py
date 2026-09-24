from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Question, MonitorRecord, Content, Competitor
from app.adapters import adapter_factory


class DashboardService:
    """仪表盘服务 - 汇总统计数据"""

    def __init__(self, db: Session):
        self.db = db

    def get_stats(self) -> Dict:
        """获取仪表盘核心统计数据"""
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

        # 基础统计
        total_questions = self.db.query(Question).count()
        enabled_questions = self.db.query(Question).filter(Question.status == True).count()
        total_platforms = len(adapter_factory.get_enabled_platforms())
        today_records = self.db.query(MonitorRecord).filter(
            MonitorRecord.detect_date == today
        ).count()

        # 近7天监测数据
        recent_records = self.db.query(MonitorRecord).filter(
            MonitorRecord.detect_date >= week_ago
        ).all()

        if recent_records:
            total = len(recent_records)
            mentioned = sum(1 for r in recent_records if r.mentioned)
            top1 = sum(1 for r in recent_records if r.rank == 1)
            ranks = [r.rank for r in recent_records if r.mentioned]

            overall_mention_rate = round(mentioned / total * 100, 1) if total else 0
            overall_top1_rate = round(top1 / total * 100, 1) if total else 0
            avg_rank = round(sum(ranks) / len(ranks), 1) if ranks else 0
        else:
            overall_mention_rate = 0
            overall_top1_rate = 0
            avg_rank = 0

        # 异常数（今天未提及的问题数）
        today_max_round = self.db.query(func.max(MonitorRecord.detect_round))\
            .filter(MonitorRecord.detect_date == today).scalar() or 1
        today_latest = self.db.query(MonitorRecord).filter(
            MonitorRecord.detect_date == today,
            MonitorRecord.detect_round == today_max_round
        ).all()
        abnormal_count = len(set(r.question_id for r in today_latest if not r.mentioned))

        # 7天趋势
        trend_7days = self._build_trend(recent_records)

        # 各平台统计
        platform_stats = self._build_platform_stats(recent_records)

        # 排名Top10和Bottom10
        top_ranking, bottom_ranking = self._build_ranking_lists(today_latest)

        return {
            "total_questions": total_questions,
            "enabled_questions": enabled_questions,
            "total_platforms": total_platforms,
            "today_records": today_records,
            "overall_mention_rate": overall_mention_rate,
            "overall_top1_rate": overall_top1_rate,
            "avg_rank": avg_rank,
            "abnormal_count": abnormal_count,
            "trend_7days": trend_7days,
            "platform_stats": platform_stats,
            "top_ranking": top_ranking,
            "bottom_ranking": bottom_ranking
        }

    def _build_trend(self, records: List) -> List[Dict]:
        """构建7天趋势数据"""
        daily = {}
        for r in records:
            if r.detect_date not in daily:
                daily[r.detect_date] = {"total": 0, "mentioned": 0, "top1": 0}
            daily[r.detect_date]["total"] += 1
            if r.mentioned:
                daily[r.detect_date]["mentioned"] += 1
            if r.rank == 1:
                daily[r.detect_date]["top1"] += 1

        result = []
        for date in sorted(daily.keys()):
            d = daily[date]
            result.append({
                "date": date,
                "mention_rate": round(d["mentioned"] / d["total"] * 100, 1) if d["total"] else 0,
                "top1_rate": round(d["top1"] / d["total"] * 100, 1) if d["total"] else 0,
                "total": d["total"]
            })
        return result

    def _build_platform_stats(self, records: List) -> List[Dict]:
        """构建各平台统计"""
        platform_data = {}
        for r in records:
            if r.platform_code not in platform_data:
                platform_data[r.platform_code] = {"total": 0, "mentioned": 0, "top1": 0, "ranks": []}
            platform_data[r.platform_code]["total"] += 1
            if r.mentioned:
                platform_data[r.platform_code]["mentioned"] += 1
                platform_data[r.platform_code]["ranks"].append(r.rank)
            if r.rank == 1:
                platform_data[r.platform_code]["top1"] += 1

        result = []
        platform_names = {"deepseek": "DeepSeek", "glm": "GLM", "minimax": "MiniMax", "doubao": "豆包", "qwen": "通义千问"}
        for code, d in platform_data.items():
            avg_rank = round(sum(d["ranks"]) / len(d["ranks"]), 1) if d["ranks"] else 0
            result.append({
                "code": code,
                "name": platform_names.get(code, code),
                "mention_rate": round(d["mentioned"] / d["total"] * 100, 1) if d["total"] else 0,
                "top1_rate": round(d["top1"] / d["total"] * 100, 1) if d["total"] else 0,
                "avg_rank": avg_rank,
                "total": d["total"]
            })
        return result

    def _build_ranking_lists(self, today_latest: List) -> tuple:
        """构建排名Top10和Bottom10"""
        question_map = {q.id: q for q in self.db.query(Question).all()}

        # 按问题聚合
        question_stats = {}
        for r in today_latest:
            if r.question_id not in question_stats:
                q = question_map.get(r.question_id)
                question_stats[r.question_id] = {
                    "question_id": r.question_id,
                    "question": q.question if q else "",
                    "category": q.category if q else "",
                    "best_rank": 999,
                    "mentioned_count": 0,
                    "platform_count": 0
                }
            question_stats[r.question_id]["platform_count"] += 1
            if r.mentioned:
                question_stats[r.question_id]["mentioned_count"] += 1
                if r.rank < question_stats[r.question_id]["best_rank"]:
                    question_stats[r.question_id]["best_rank"] = r.rank

        items = list(question_stats.values())
        for item in items:
            item["best_rank"] = item["best_rank"] if item["best_rank"] < 999 else 0
            item["mention_rate"] = round(item["mentioned_count"] / item["platform_count"] * 100, 1) if item["platform_count"] else 0

        # Top10：排名最好的
        top = sorted([i for i in items if i["best_rank"] > 0], key=lambda x: x["best_rank"])[:10]
        # Bottom10：未提及或排名靠后的
        bottom = sorted(items, key=lambda x: (x["mentioned_count"], -x["best_rank"] if x["best_rank"] else 999))[:10]

        return top, bottom

    def get_doctor_stats(self, user_id: int) -> Dict:
        """医生视角仪表盘统计"""
        from app.models.semantic import Semantic
        from app.models.article import ArticleDraft
        from app.models.monitor import MonitorRecord
        from app.adapters import adapter_factory
        from datetime import datetime, timedelta

        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

        # 基础统计
        semantics = self.db.query(Semantic).filter(Semantic.user_id == user_id).all()
        active_semantics = sum(1 for s in semantics if s.is_active)
        article_count = self.db.query(ArticleDraft).filter(ArticleDraft.user_id == user_id).count()
        platforms = adapter_factory.get_enabled_platforms()

        semantic_ids = [s.id for s in semantics]

        # 最新GEO/AEO数据
        overall_geo_rate = 0
        overall_aeo_rate = 0
        trend_7days = []
        top_semantics = []
        bottom_semantics = []
        platform_stats = []
        last_refresh = None

        if semantic_ids:
            latest_date = self.db.query(func.max(MonitorRecord.detect_date)).filter(
                MonitorRecord.semantic_id.in_(semantic_ids),
                MonitorRecord.detect_type == "doctor"
            ).scalar()
            last_refresh = latest_date

            if latest_date:
                latest_records = self.db.query(MonitorRecord).filter(
                    MonitorRecord.semantic_id.in_(semantic_ids),
                    MonitorRecord.detect_type == "doctor",
                    MonitorRecord.detect_date == latest_date,
                    MonitorRecord.detect_round == 99
                ).all()

                if latest_records:
                    total_geo = sum(1 for r in latest_records if r.mentioned)
                    total_aeo = sum(1 for r in latest_records if r.cite_count > 0)
                    overall_geo_rate = round(total_geo / len(latest_records) * 100, 1)
                    overall_aeo_rate = round(total_aeo / len(latest_records) * 100, 1)

                    # 各语义统计
                    sem_map = {s.id: s for s in semantics}
                    sem_stats = {}
                    for r in latest_records:
                        if r.semantic_id not in sem_stats:
                            sem_stats[r.semantic_id] = {"total": 0, "geo": 0, "aeo": 0, "best_rank": 999}
                        sem_stats[r.semantic_id]["total"] += 1
                        if r.mentioned:
                            sem_stats[r.semantic_id]["geo"] += 1
                            if r.rank < sem_stats[r.semantic_id]["best_rank"]:
                                sem_stats[r.semantic_id]["best_rank"] = r.rank
                        if r.cite_count > 0:
                            sem_stats[r.semantic_id]["aeo"] += 1

                    ranked = []
                    for sid, st in sem_stats.items():
                        s = sem_map.get(sid)
                        ranked.append({
                            "semantic_id": sid,
                            "question": s.question if s else "",
                            "geo_rate": round(st["geo"] / st["total"] * 100, 1) if st["total"] else 0,
                            "aeo_rate": round(st["aeo"] / st["total"] * 100, 1) if st["total"] else 0,
                            "best_rank": st["best_rank"] if st["best_rank"] < 999 else 0,
                        })
                    top_semantics = sorted(ranked, key=lambda x: (-x["geo_rate"], x["best_rank"]))[:5]
                    bottom_semantics = sorted(ranked, key=lambda x: (x["geo_rate"], -x["best_rank"]))[:5]

                    # 各平台统计
                    plat_data = {}
                    for r in latest_records:
                        if r.platform_code not in plat_data:
                            plat_data[r.platform_code] = {"total": 0, "geo": 0, "aeo": 0}
                        plat_data[r.platform_code]["total"] += 1
                        if r.mentioned:
                            plat_data[r.platform_code]["geo"] += 1
                        if r.cite_count > 0:
                            plat_data[r.platform_code]["aeo"] += 1
                    platform_names = {"deepseek": "DeepSeek", "glm": "GLM", "minimax": "MiniMax", "doubao": "豆包", "qwen": "通义千问"}
                    for code, d in plat_data.items():
                        platform_stats.append({
                            "code": code,
                            "name": platform_names.get(code, code),
                            "geo_rate": round(d["geo"] / d["total"] * 100, 1) if d["total"] else 0,
                            "aeo_rate": round(d["aeo"] / d["total"] * 100, 1) if d["total"] else 0,
                            "total": d["total"],
                        })

            # 7天趋势
            trend_records = self.db.query(MonitorRecord).filter(
                MonitorRecord.semantic_id.in_(semantic_ids),
                MonitorRecord.detect_type == "doctor",
                MonitorRecord.detect_date >= week_ago
            ).all()
            daily = {}
            for r in trend_records:
                if r.detect_date not in daily:
                    daily[r.detect_date] = {"total": 0, "geo": 0, "aeo": 0}
                daily[r.detect_date]["total"] += 1
                if r.mentioned:
                    daily[r.detect_date]["geo"] += 1
                if r.cite_count > 0:
                    daily[r.detect_date]["aeo"] += 1
            for date in sorted(daily.keys()):
                d = daily[date]
                trend_7days.append({
                    "date": date,
                    "geo_rate": round(d["geo"] / d["total"] * 100, 1) if d["total"] else 0,
                    "aeo_rate": round(d["aeo"] / d["total"] * 100, 1) if d["total"] else 0,
                })

        return {
            "total_semantics": len(semantics),
            "active_semantics": active_semantics,
            "article_count": article_count,
            "overall_geo_rate": overall_geo_rate,
            "overall_aeo_rate": overall_aeo_rate,
            "trend_7days": trend_7days,
            "platform_stats": platform_stats,
            "top_semantics": top_semantics,
            "bottom_semantics": bottom_semantics,
            "last_refresh": last_refresh,
            "platforms": platforms,
        }
