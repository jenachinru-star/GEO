import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional, Callable
from sqlalchemy.orm import Session

from app.adapters import adapter_factory
from app.engines.parser import AnswerParser
from app.models import Question, MonitorRecord, Competitor, CompetitorRecord
from app.config import settings

logger = logging.getLogger(__name__)


class CollectorEngine:
    """采集引擎 - 负责调度多平台采集与解析（串行模式，稳定优先）"""

    def __init__(self, db: Session):
        self.db = db
        self.parser = AnswerParser(settings.brand_aliases)

    def query_single_platform(self, platform_code: str, question: str,
                               retries: int = 2) -> tuple[bool, str]:
        """向单个平台提问，带重试"""
        adapter = adapter_factory.get_adapter(platform_code)
        if not adapter:
            return False, f"平台 {platform_code} 未配置"

        last_error = "未知错误"
        for attempt in range(retries):
            try:
                if attempt > 0:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"重试 {platform_code}，等待 {wait:.1f}s")
                    time.sleep(wait)

                logger.info(f"调用 {platform_code} API: {question[:50]}...")
                result = adapter.query(question)

                if result.success:
                    logger.info(f"{platform_code} 调用成功，回答长度: {len(result.answer)}")
                    return True, result.answer
                else:
                    last_error = result.error or "未知错误"
                    logger.warning(f"{platform_code} 调用失败: {last_error[:200]}")
                    if attempt < retries - 1:
                        continue
                    return False, last_error
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                logger.error(f"{platform_code} 调用异常: {last_error}")
                if attempt < retries - 1:
                    continue
                return False, last_error

        return False, last_error

    def collect_one_question(self, question: Question, detect_round: int = 1) -> List[MonitorRecord]:
        """采集单个问题在所有平台的回答（串行模式）"""
        records = []
        today = datetime.now().strftime("%Y-%m-%d")
        platforms = adapter_factory.get_enabled_platforms()

        if not platforms:
            logger.warning("没有已启用的平台")
            return records

        logger.info(f"开始采集问题 [{question.id}]: {question.question}")

        # 串行查询各平台（稳定优先，避免并发问题）
        for platform_code in platforms:
            logger.info(f"  -> 采集平台: {platform_code}")
            success, answer = self.query_single_platform(platform_code, question.question)

            if success and answer:
                parse_result = self.parser.parse(answer)
                logger.info(f"  -> {platform_code} 解析结果: 提及={parse_result.mentioned}, 排名={parse_result.rank}")
                record = MonitorRecord(
                    question_id=question.id,
                    platform_code=platform_code,
                    rank=parse_result.rank,
                    mentioned=parse_result.mentioned,
                    sentiment=parse_result.sentiment,
                    raw_answer=answer,
                    detect_date=today,
                    detect_round=detect_round
                )
            else:
                logger.error(f"  -> {platform_code} 采集失败: {answer[:100]}")
                record = MonitorRecord(
                    question_id=question.id,
                    platform_code=platform_code,
                    rank=0,
                    mentioned=False,
                    sentiment=0.0,
                    raw_answer=f"采集失败: {answer[:500]}",
                    detect_date=today,
                    detect_round=detect_round
                )

            records.append(record)
            # 平台之间加延迟，避免限流
            time.sleep(1)

        # 批量入库（先删除旧记录，避免唯一约束冲突）
        if records:
            try:
                # 删除同一问题同一轮次的旧记录
                self.db.query(MonitorRecord).filter(
                    MonitorRecord.question_id == question.id,
                    MonitorRecord.detect_date == today,
                    MonitorRecord.detect_round == detect_round
                ).delete(synchronize_session=False)
                self.db.commit()

                self.db.add_all(records)
                self.db.commit()
                logger.info(f"问题 [{question.id}] 采集完成，入库 {len(records)} 条记录")
            except Exception as e:
                self.db.rollback()
                logger.error(f"入库失败: {e}")

        # 同时采集竞品数据
        self._collect_competitors(question, records)

        return records

    def collect_one_semantic(self, semantic, profile, detect_round: int = 99) -> List[MonitorRecord]:
        """采集单个语义在所有平台的GEO/AEO数据（医生维度）

        Args:
            semantic: Semantic模型对象
            profile: DoctorProfile模型对象
            detect_round: 采集轮次，医生维度固定用99
        """
        from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer

        records = []
        today = datetime.now().strftime("%Y-%m-%d")
        platforms = adapter_factory.get_enabled_platforms()

        if not platforms:
            logger.warning("没有已启用的平台")
            return records

        # 构建GEO/AEO解析器
        analyzer = GEOAEOAnalyzer(
            doctor_name=profile.real_name,
            hospital=profile.hospital,
            department=profile.department,
            self_intro=profile.self_intro_template,
        )

        logger.info(f"开始GEO/AEO采集语义 [{semantic.id}]: {semantic.question}")

        for platform_code in platforms:
            logger.info(f"  -> 采集平台: {platform_code}")
            success, answer = self.query_single_platform(platform_code, semantic.question)

            if success and answer:
                result = analyzer.analyze(answer)
                logger.info(f"  -> {platform_code}: GEO={'是' if result.geo_mentioned else '否'}(排名{result.geo_rank}), AEO={'是' if result.aeo_cited else '否'}")
                record = MonitorRecord(
                    question_id=semantic.id,  # 关键：填semantic.id，不是0！用于唯一约束
                    semantic_id=semantic.id,  # 冗余，用于清晰查询
                    platform_code=platform_code,
                    rank=result.geo_rank,
                    mentioned=result.geo_mentioned,
                    sentiment=0.0,
                    raw_answer=answer,
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=1 if result.geo_mentioned else 0,
                    cite_count=1 if result.aeo_cited else 0,
                    aeo_confidence=result.aeo_confidence,
                )
            else:
                logger.error(f"  -> {platform_code} 采集失败: {answer[:100]}")
                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=0,
                    mentioned=False,
                    sentiment=0.0,
                    raw_answer=f"采集失败: {answer[:500]}",
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=0,
                    cite_count=0,
                    aeo_confidence=0.0,
                )

            records.append(record)
            time.sleep(1)

        # 批量入库（先按semantic_id删旧记录，不能按question_id删！）
        if records:
            try:
                self.db.query(MonitorRecord).filter(
                    MonitorRecord.semantic_id == semantic.id,
                    MonitorRecord.detect_date == today,
                    MonitorRecord.detect_round == detect_round
                ).delete(synchronize_session=False)
                self.db.commit()

                self.db.add_all(records)
                self.db.commit()
                logger.info(f"语义 [{semantic.id}] GEO/AEO采集完成，入库 {len(records)} 条记录")
            except Exception as e:
                self.db.rollback()
                logger.error(f"GEO/AEO入库失败: {e}")

        return records

    def collect_all_semantics(self, user_id: int, detect_round: int = 99) -> Dict:
        """采集指定用户所有启用语义的GEO/AEO数据"""
        from app.models.semantic import Semantic
        from app.models.doctor import DoctorProfile

        profile = self.db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
        if not profile:
            return {"total": 0, "success": 0, "error": "未找到医生Profile"}

        semantics = self.db.query(Semantic).filter(
            Semantic.user_id == user_id,
            Semantic.is_active == True
        ).all()

        total = len(semantics)
        success_count = 0
        all_records = []

        logger.info(f"开始用户 [{user_id}] 全量GEO/AEO采集，共 {total} 个语义")

        for i, semantic in enumerate(semantics):
            try:
                records = self.collect_one_semantic(semantic, profile, detect_round)
                all_records.extend(records)
                success_count += 1
            except Exception as e:
                logger.error(f"采集语义失败 [{semantic.question}]: {e}")
            if i < total - 1:
                time.sleep(2)

        # 更新semantic表的geo_rate/aeo_rate缓存
        self._update_semantic_rates(user_id)

        logger.info(f"用户 [{user_id}] GEO/AEO采集完成: {success_count}/{total}")
        return {
            "total": total,
            "success": success_count,
            "records_count": len(all_records),
            "platforms": adapter_factory.get_enabled_platforms(),
        }

    def _update_semantic_rates(self, user_id: int):
        """更新semantic表的geo_rate/aeo_rate缓存字段（不碰article_count）"""
        from app.models.semantic import Semantic

        semantics = self.db.query(Semantic).filter(Semantic.user_id == user_id).all()
        platforms = adapter_factory.get_enabled_platforms()
        total_platforms = len(platforms) if platforms else 1

        for s in semantics:
            records = self.db.query(MonitorRecord).filter(
                MonitorRecord.semantic_id == s.id,
                MonitorRecord.detect_type == "doctor"
            ).order_by(MonitorRecord.detect_time.desc()).limit(total_platforms).all()

            if records:
                geo_count = sum(1 for r in records if r.mentioned)
                aeo_count = sum(1 for r in records if r.cite_count > 0)
                s.geo_rate = round(geo_count / len(records) * 100, 1)
                s.aeo_rate = round(aeo_count / len(records) * 100, 1)

        self.db.commit()

    def _collect_competitors(self, question: Question, records: List[MonitorRecord]):
        """采集竞品提及情况"""
        try:
            competitors = self.db.query(Competitor).filter(Competitor.status == True).all()
            if not competitors:
                return

            today = datetime.now().strftime("%Y-%m-%d")
            competitor_aliases = {}
            for comp in competitors:
                aliases = [comp.name]
                if comp.aliases:
                    aliases.extend([a.strip() for a in comp.aliases.split(",") if a.strip()])
                competitor_aliases[comp.id] = aliases

            for record in records:
                if record.raw_answer and not record.raw_answer.startswith("采集失败"):
                    comp_results = self.parser.parse_competitors(record.raw_answer, competitor_aliases)
                    for comp_id, (mentioned, rank) in comp_results.items():
                        comp_record = CompetitorRecord(
                            competitor_id=comp_id,
                            question_id=question.id,
                            platform_code=record.platform_code,
                            rank=rank,
                            mentioned=mentioned,
                            detect_date=today
                        )
                        self.db.add(comp_record)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"竞品采集失败: {e}")

    def collect_all(self, detect_round: int = 1,
                    progress_callback: Optional[Callable] = None) -> Dict:
        """全量采集所有启用的问题"""
        questions = self.db.query(Question).filter(Question.status == True).all()
        total = len(questions)
        success_count = 0
        all_records = []

        logger.info(f"开始全量采集，共 {total} 个问题")

        for i, question in enumerate(questions):
            try:
                logger.info(f"[{i+1}/{total}] 采集问题: {question.question}")
                records = self.collect_one_question(question, detect_round)
                all_records.extend(records)
                success_count += 1
            except Exception as e:
                logger.error(f"采集问题失败 [{question.question}]: {e}")

            if progress_callback:
                progress_callback(i + 1, total, question.question)

            # 问题之间加延迟
            if i < total - 1:
                time.sleep(2)

        logger.info(f"全量采集完成: {success_count}/{total} 成功, {len(all_records)} 条记录")

        return {
            "total": total,
            "success": success_count,
            "records_count": len(all_records),
            "platforms": adapter_factory.get_enabled_platforms()
        }

    def collect_single_question_now(self, question_id: int) -> List[MonitorRecord]:
        """立即采集单个问题（手动触发）"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return []
        # 手动触发用round=99标识
        return self.collect_one_question(question, detect_round=99)
