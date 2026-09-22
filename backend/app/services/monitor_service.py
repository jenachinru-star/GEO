from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models import Question, MonitorRecord, Semantic
from app.engines import CollectorEngine


class MonitorService:
    """监测服务 - 监测数据查询与统计"""

    def __init__(self, db: Session):
        self.db = db

    def _get_user_question_ids(self, user_id: int) -> List[int]:
        """获取用户所有问题ID"""
        return [r[0] for r in self.db.query(Question.id).filter(Question.user_id == user_id).all()]

    def _get_user_semantic_ids(self, user_id: int) -> List[int]:
        """获取用户所有语义ID"""
        return [r[0] for r in self.db.query(Semantic.id).filter(Semantic.user_id == user_id).all()]

    def get_question_list(self, category: str = None, status: bool = None,
                          keyword: str = None, page: int = 1, page_size: int = 20,
                          user_id: int = None) -> Dict:
        """获取问题列表"""
        query = self.db.query(Question)
        if user_id is not None:
            query = query.filter(Question.user_id == user_id)
        if category:
            query = query.filter(Question.category == category)
        if status is not None:
            query = query.filter(Question.status == status)
        if keyword:
            query = query.filter(Question.question.contains(keyword))

        total = query.count()
        items = query.order_by(Question.priority.desc(), Question.id.desc())\
            .offset((page - 1) * page_size).limit(page_size).all()

        return {"total": total, "items": items, "page": page, "page_size": page_size}

    def get_monitor_records(self, question_id: int = None, platform_code: str = None,
                             start_date: str = None, end_date: str = None,
                             page: int = 1, page_size: int = 50,
                             user_id: int = None) -> Dict:
        """获取监测记录"""
        query = self.db.query(MonitorRecord)
        if user_id is not None:
            q_ids = self._get_user_question_ids(user_id)
            s_ids = self._get_user_semantic_ids(user_id)
            all_ids = list(set(q_ids + s_ids))
            if all_ids:
                query = query.filter(
                    or_(MonitorRecord.question_id.in_(all_ids),
                        MonitorRecord.semantic_id.in_(all_ids))
                )
            else:
                query = query.filter(False)  # 用户无任何问题/语义，返回空
        if question_id:
            query = query.filter(MonitorRecord.question_id == question_id)
        if platform_code:
            query = query.filter(MonitorRecord.platform_code == platform_code)
        if start_date:
            query = query.filter(MonitorRecord.detect_date >= start_date)
        if end_date:
            query = query.filter(MonitorRecord.detect_date <= end_date)

        total = query.count()
        items = query.order_by(MonitorRecord.detect_time.desc())\
            .offset((page - 1) * page_size).limit(page_size).all()

        return {"total": total, "items": items}

    def get_question_matrix(self, question_ids: List[int] = None,
                            platforms: List[str] = None,
                            date: str = None,
                            user_id: int = None) -> List[Dict]:
        """获取问题×平台的矩阵数据（最新一轮）"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        # 找当天最大的detect_round
        max_round = self.db.query(func.max(MonitorRecord.detect_round))\
            .filter(MonitorRecord.detect_date == date).scalar() or 1

        query = self.db.query(MonitorRecord).filter(
            MonitorRecord.detect_date == date,
            MonitorRecord.detect_round == max_round
        )
        if user_id is not None:
            q_ids = self._get_user_question_ids(user_id)
            s_ids = self._get_user_semantic_ids(user_id)
            all_ids = list(set(q_ids + s_ids))
            if all_ids:
                query = query.filter(
                    or_(MonitorRecord.question_id.in_(all_ids),
                        MonitorRecord.semantic_id.in_(all_ids))
                )
            else:
                query = query.filter(False)
        if question_ids:
            query = query.filter(MonitorRecord.question_id.in_(question_ids))
        if platforms:
            query = query.filter(MonitorRecord.platform_code.in_(platforms))

        records = query.all()

        # 组织成矩阵
        matrix = {}
        question_map = {q.id: q for q in self.db.query(Question).all()}
        if user_id is not None:
            question_map = {q.id: q for q in self.db.query(Question).filter(Question.user_id == user_id).all()}

        for r in records:
            if r.question_id not in matrix:
                q = question_map.get(r.question_id)
                matrix[r.question_id] = {
                    "question_id": r.question_id,
                    "question": q.question if q else "",
                    "category": q.category if q else "",
                    "platforms": {}
                }
            matrix[r.question_id]["platforms"][r.platform_code] = {
                "rank": r.rank,
                "mentioned": r.mentioned,
                "sentiment": r.sentiment,
                "record_id": r.id
            }

        return list(matrix.values())

    def get_question_trend(self, question_id: int, platform_code: str = None,
                            days: int = 7,
                            user_id: int = None) -> List[Dict]:
        """获取单个问题的趋势数据"""
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        query = self.db.query(MonitorRecord).filter(
            MonitorRecord.question_id == question_id,
            MonitorRecord.detect_date >= start_date
        )
        if user_id is not None:
            q_ids = self._get_user_question_ids(user_id)
            s_ids = self._get_user_semantic_ids(user_id)
            all_ids = list(set(q_ids + s_ids))
            if question_id not in all_ids:
                return []  # 问题不属于该用户，返回空
        if platform_code:
            query = query.filter(MonitorRecord.platform_code == platform_code)

        records = query.order_by(MonitorRecord.detect_date).all()

        # 按日期+平台聚合（取当天最好排名）
        trend = {}
        for r in records:
            key = f"{r.detect_date}_{r.platform_code}"
            if key not in trend:
                trend[key] = {
                    "date": r.detect_date,
                    "platform": r.platform_code,
                    "best_rank": r.rank if r.mentioned else 999,
                    "mentioned": r.mentioned,
                    "avg_sentiment": r.sentiment
                }
            else:
                if r.mentioned and r.rank < trend[key]["best_rank"]:
                    trend[key]["best_rank"] = r.rank
                if r.mentioned:
                    trend[key]["mentioned"] = True

        result = []
        for v in trend.values():
            v["rank"] = v["best_rank"] if v["best_rank"] < 999 else 0
            del v["best_rank"]
            result.append(v)

        return sorted(result, key=lambda x: (x["date"], x["platform"]))

    def trigger_collect(self, question_id: int = None) -> Dict:
        """触发采集"""
        collector = CollectorEngine(self.db)
        if question_id:
            records = collector.collect_single_question_now(question_id)
            return {
                "total": 1,
                "success": 1 if records else 0,
                "records_count": len(records),
                "platforms": [r.platform_code for r in records]
            }
        else:
            return collector.collect_all(detect_round=1)
