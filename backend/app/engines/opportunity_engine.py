"""
内容机会识别引擎 — 扫描监测数据，自动识别内容创作机会。

机会类型：
- missing_mention: AI回答中未提及医生 → 需要写内容提升曝光
- missing_citation: 有提及但无来源引用 → 需要写权威内容并发布到可引用平台
- low_rank: 排名靠后（>3） → 需要优化内容质量和关键词
- competitor_gap: 竞品被推荐更多 → 需要差异化内容
"""
import json
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.semantic import Semantic
from app.models.monitor import MonitorRecord
from app.models.content_opportunity import ContentOpportunity
from app.models.doctor import DoctorProfile

logger = logging.getLogger(__name__)


class OpportunityEngine:
    def __init__(self, db: Session):
        self.db = db

    def scan(self, user_id: int) -> dict:
        """扫描用户的所有语义，生成内容机会"""
        semantics = self.db.query(Semantic).filter(
            Semantic.user_id == user_id,
            Semantic.is_active == True
        ).all()

        if not semantics:
            return {"total": 0, "new": 0, "message": "没有启用的语义"}

        semantic_ids = [s.id for s in semantics]

        # 获取最新一轮采集记录
        latest_date = self.db.query(func.max(MonitorRecord.detect_date)).filter(
            MonitorRecord.semantic_id.in_(semantic_ids),
            MonitorRecord.detect_type == "doctor"
        ).scalar()

        if not latest_date:
            return {"total": 0, "new": 0, "message": "没有采集数据，请先执行GEO刷新"}

        latest_records = self.db.query(MonitorRecord).filter(
            MonitorRecord.semantic_id.in_(semantic_ids),
            MonitorRecord.detect_type == "doctor",
            MonitorRecord.detect_date == latest_date,
            MonitorRecord.detect_round == 99
        ).all()

        # 按 semantic_id 分组
        records_by_semantic = {}
        for r in latest_records:
            if r.semantic_id not in records_by_semantic:
                records_by_semantic[r.semantic_id] = []
            records_by_semantic[r.semantic_id].append(r)

        new_count = 0
        for semantic in semantics:
            records = records_by_semantic.get(semantic.id, [])
            if not records:
                continue

            total = len(records)
            mentioned_count = sum(1 for r in records if r.mentioned)
            cited_count = sum(1 for r in records if r.cite_count and r.cite_count > 0)
            avg_rank = sum(r.rank for r in records if r.mentioned and r.rank > 0) / max(1, mentioned_count)
            mention_rate = mentioned_count / total if total > 0 else 0

            # 1. missing_mention: 提及率 < 50%
            if mention_rate < 0.5:
                opp = self._create_or_update(
                    user_id, semantic, "missing_mention",
                    priority=80 - mention_rate * 50,  # 提及率越低优先级越高
                    evidence={
                        "mention_rate": round(mention_rate * 100, 1),
                        "mentioned_count": mentioned_count,
                        "total_count": total,
                        "platforms_missing": [r.platform_code for r in records if not r.mentioned],
                    }
                )
                if opp: new_count += 1

            # 2. missing_citation: 有提及但引用率 < 30%
            elif cited_count / max(1, mentioned_count) < 0.3:
                opp = self._create_or_update(
                    user_id, semantic, "missing_citation",
                    priority=60,
                    evidence={
                        "citation_rate": round(cited_count / max(1, mentioned_count) * 100, 1),
                        "cited_count": cited_count,
                        "mentioned_count": mentioned_count,
                    }
                )
                if opp: new_count += 1

            # 3. low_rank: 平均排名 > 3
            if mentioned_count > 0 and avg_rank > 3:
                opp = self._create_or_update(
                    user_id, semantic, "low_rank",
                    priority=50,
                    evidence={"avg_rank": round(avg_rank, 1), "mentioned_count": mentioned_count}
                )
                if opp: new_count += 1

        return {"total": len(semantics), "new": new_count, "message": f"扫描完成，新增 {new_count} 个内容机会"}

    def _create_or_update(self, user_id: int, semantic: Semantic,
                          opp_type: str, priority: float, evidence: dict) -> ContentOpportunity | None:
        """创建或更新内容机会（同一语义+同一类型不重复创建 open 状态的）"""
        existing = self.db.query(ContentOpportunity).filter(
            ContentOpportunity.question_id == semantic.id,
            ContentOpportunity.opportunity_type == opp_type,
            ContentOpportunity.status == "open"
        ).first()

        if existing:
            # 更新证据和优先级
            existing.evidence_json = json.dumps(evidence, ensure_ascii=False)
            existing.priority_score = priority
            self.db.commit()
            return None

        # 获取 doctor_id
        profile = self.db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
        doctor_id = profile.id if profile else None

        # 获取 workspace_id
        from app.services.workspace_service import get_user_workspace_id
        workspace_id = get_user_workspace_id(self.db, user_id)

        opp = ContentOpportunity(
            workspace_id=workspace_id,
            doctor_id=doctor_id,
            question_id=semantic.id,
            opportunity_type=opp_type,
            priority_score=priority,
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            status="open",
        )
        self.db.add(opp)
        self.db.commit()
        self.db.refresh(opp)
        return opp

    def dismiss(self, opp_id: int, user_id: int) -> bool:
        """忽略机会"""
        from datetime import datetime
        opp = self.db.query(ContentOpportunity).filter(
            ContentOpportunity.id == opp_id,
            ContentOpportunity.status == "open"
        ).first()
        if not opp:
            return False
        opp.status = "dismissed"
        opp.resolved_at = datetime.now()
        self.db.commit()
        return True
