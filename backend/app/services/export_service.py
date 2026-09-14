"""数据导出服务 - 支持Excel和CSV格式导出"""
import io
import csv
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models import MonitorRecord, Question, Content, Knowledge, Competitor
from app.config import settings


class ExportService:
    """数据导出服务"""

    PLATFORM_NAMES = {
        "deepseek": "DeepSeek",
        "glm": "GLM",
        "minimax": "MiniMax",
        "doubao": "豆包",
        "qwen": "通义千问"
    }

    CATEGORY_NAMES = {
        "brand": "品牌类",
        "tech": "技术类",
        "industry": "行业类",
        "competitor": "竞品类",
        "general": "综合类"
    }

    @staticmethod
    def _style_header(ws, row_num: int, col_count: int):
        """设置表头样式"""
        header_fill = PatternFill(start_color="0EA5E9", end_color="0EA5E9", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        for col in range(1, col_count + 1):
            cell = ws.cell(row=row_num, column=col)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border

    @staticmethod
    def _style_data(ws, start_row: int, end_row: int, col_count: int):
        """设置数据样式"""
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        for row in range(start_row, end_row + 1):
            for col in range(1, col_count + 1):
                cell = ws.cell(row=row, column=col)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center", wrap_text=True)

    @classmethod
    def export_monitor_records(cls, db: Session, question_id: Optional[int] = None,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> bytes:
        """导出监测记录为Excel"""
        wb = Workbook()
        ws = wb.active
        ws.title = "监测记录"

        # 表头
        headers = ["ID", "监测问题", "问题分类", "AI平台", "是否提及", "排名", "情感分",
                   "检测日期", "检测轮次", "检测时间", "原始回答"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        cls._style_header(ws, 1, len(headers))

        # 查询数据
        query = db.query(MonitorRecord, Question).join(Question, MonitorRecord.question_id == Question.id)
        if question_id:
            query = query.filter(MonitorRecord.question_id == question_id)
        if start_date:
            query = query.filter(MonitorRecord.detect_date >= start_date)
        if end_date:
            query = query.filter(MonitorRecord.detect_date <= end_date)
        records = query.order_by(MonitorRecord.detect_date.desc(), MonitorRecord.id.desc()).all()

        # 写入数据
        for row_idx, (record, question) in enumerate(records, 2):
            ws.cell(row=row_idx, column=1, value=record.id)
            ws.cell(row=row_idx, column=2, value=question.question)
            ws.cell(row=row_idx, column=3, value=cls.CATEGORY_NAMES.get(question.category, question.category))
            ws.cell(row=row_idx, column=4, value=cls.PLATFORM_NAMES.get(record.platform_code, record.platform_code))
            ws.cell(row=row_idx, column=5, value="是" if record.mentioned else "否")
            ws.cell(row=row_idx, column=6, value=record.rank if record.rank > 0 else "未提及")
            ws.cell(row=row_idx, column=7, value=round(record.sentiment, 2))
            ws.cell(row=row_idx, column=8, value=record.detect_date)
            ws.cell(row=row_idx, column=9, value=record.detect_round)
            ws.cell(row=row_idx, column=10, value=record.detect_time.strftime("%Y-%m-%d %H:%M:%S") if record.detect_time else "")
            ws.cell(row=row_idx, column=11, value=record.raw_answer[:1000] if record.raw_answer else "")

        if records:
            cls._style_data(ws, 2, len(records) + 1, len(headers))

        # 调整列宽
        col_widths = [6, 30, 10, 12, 8, 8, 8, 12, 8, 18, 60]
        for col, width in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width

        # 冻结首行
        ws.freeze_panes = "A2"

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_questions(cls, db: Session) -> bytes:
        """导出问题列表为Excel"""
        wb = Workbook()
        ws = wb.active
        ws.title = "监测问题"

        headers = ["ID", "问题内容", "分类", "标签", "优先级", "状态", "创建时间"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        cls._style_header(ws, 1, len(headers))

        questions = db.query(Question).order_by(Question.priority.desc(), Question.id).all()
        for row_idx, q in enumerate(questions, 2):
            ws.cell(row=row_idx, column=1, value=q.id)
            ws.cell(row=row_idx, column=2, value=q.question)
            ws.cell(row=row_idx, column=3, value=cls.CATEGORY_NAMES.get(q.category, q.category))
            ws.cell(row=row_idx, column=4, value=q.tags)
            ws.cell(row=row_idx, column=5, value=q.priority)
            ws.cell(row=row_idx, column=6, value="启用" if q.status else "禁用")
            ws.cell(row=row_idx, column=7, value=q.created_at.strftime("%Y-%m-%d %H:%M:%S") if q.created_at else "")

        if questions:
            cls._style_data(ws, 2, len(questions) + 1, len(headers))

        col_widths = [6, 40, 10, 20, 8, 8, 18]
        for col, width in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width
        ws.freeze_panes = "A2"

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_knowledge(cls, db: Session) -> bytes:
        """导出知识库为Excel"""
        wb = Workbook()
        ws = wb.active
        ws.title = "知识库"

        headers = ["ID", "标题", "分类", "级别", "内容", "标签", "状态", "版本", "更新时间"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        cls._style_header(ws, 1, len(headers))

        level_names = {"public": "公开", "internal": "内部", "confidential": "涉密"}
        knowledge_list = db.query(Knowledge).order_by(Knowledge.category, Knowledge.id).all()
        for row_idx, k in enumerate(knowledge_list, 2):
            ws.cell(row=row_idx, column=1, value=k.id)
            ws.cell(row=row_idx, column=2, value=k.title)
            ws.cell(row=row_idx, column=3, value=k.category)
            ws.cell(row=row_idx, column=4, value=level_names.get(k.level, k.level))
            ws.cell(row=row_idx, column=5, value=k.content)
            ws.cell(row=row_idx, column=6, value=k.tags)
            ws.cell(row=row_idx, column=7, value="启用" if k.status else "禁用")
            ws.cell(row=row_idx, column=8, value=k.version)
            ws.cell(row=row_idx, column=9, value=k.updated_at.strftime("%Y-%m-%d %H:%M:%S") if k.updated_at else "")

        if knowledge_list:
            cls._style_data(ws, 2, len(knowledge_list) + 1, len(headers))

        col_widths = [6, 20, 12, 8, 60, 15, 8, 6, 18]
        for col, width in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width
        ws.freeze_panes = "A2"

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_content(cls, db: Session) -> bytes:
        """导出内容资产为Excel"""
        wb = Workbook()
        ws = wb.active
        ws.title = "内容资产"

        headers = ["ID", "标题", "分类", "标签", "摘要", "发布链接", "发布平台",
                   "引用次数", "效果评分", "发布时间", "创建时间"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        cls._style_header(ws, 1, len(headers))

        contents = db.query(Content).order_by(Content.created_at.desc()).all()
        for row_idx, c in enumerate(contents, 2):
            ws.cell(row=row_idx, column=1, value=c.id)
            ws.cell(row=row_idx, column=2, value=c.title)
            ws.cell(row=row_idx, column=3, value=c.category)
            ws.cell(row=row_idx, column=4, value=c.tags)
            ws.cell(row=row_idx, column=5, value=c.summary)
            ws.cell(row=row_idx, column=6, value=c.publish_url)
            ws.cell(row=row_idx, column=7, value=c.publish_site)
            ws.cell(row=row_idx, column=8, value=c.citation_count or 0)
            ws.cell(row=row_idx, column=9, value=round(c.effect_score or 0, 2))
            ws.cell(row=row_idx, column=10, value=c.publish_time.strftime("%Y-%m-%d") if c.publish_time else "")
            ws.cell(row=row_idx, column=11, value=c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "")

        if contents:
            cls._style_data(ws, 2, len(contents) + 1, len(headers))

        col_widths = [6, 25, 10, 15, 40, 30, 12, 8, 8, 12, 18]
        for col, width in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width
        ws.freeze_panes = "A2"

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_full_report(cls, db: Session) -> bytes:
        """导出完整报告（多Sheet）"""
        wb = Workbook()

        # Sheet1: 概览
        ws_summary = wb.active
        ws_summary.title = "概览"
        ws_summary.cell(row=1, column=1, value="GEO监测报告")
        ws_summary.cell(row=1, column=1).font = Font(bold=True, size=16, color="0EA5E9")
        ws_summary.cell(row=2, column=1, value=f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        ws_summary.cell(row=3, column=1, value=f"品牌: {settings.DEFAULT_BRAND_NAME}")

        total_questions = db.query(Question).filter(Question.status == True).count()
        total_records = db.query(MonitorRecord).count()
        mentioned_records = db.query(MonitorRecord).filter(MonitorRecord.mentioned == True).count()
        mention_rate = (mentioned_records / total_records * 100) if total_records > 0 else 0

        ws_summary.cell(row=5, column=1, value="核心指标")
        ws_summary.cell(row=5, column=1).font = Font(bold=True, size=12)
        metrics = [
            ("监测问题数", total_questions),
            ("采集记录总数", total_records),
            ("提及记录数", mentioned_records),
            ("整体提及率", f"{mention_rate:.1f}%"),
            ("已启用平台", ", ".join([cls.PLATFORM_NAMES.get(p, p) for p in settings.get_enabled_platforms()]))
        ]
        for i, (name, value) in enumerate(metrics, 6):
            ws_summary.cell(row=i, column=1, value=name)
            ws_summary.cell(row=i, column=2, value=value)

        ws_summary.column_dimensions['A'].width = 20
        ws_summary.column_dimensions['B'].width = 40

        # Sheet2: 监测记录
        ws_records = wb.create_sheet("监测记录")
        headers = ["ID", "监测问题", "问题分类", "AI平台", "是否提及", "排名", "情感分",
                   "检测日期", "检测轮次", "原始回答"]
        for col, header in enumerate(headers, 1):
            ws_records.cell(row=1, column=col, value=header)
        cls._style_header(ws_records, 1, len(headers))

        records = db.query(MonitorRecord, Question).join(
            Question, MonitorRecord.question_id == Question.id
        ).order_by(MonitorRecord.detect_date.desc(), MonitorRecord.id.desc()).limit(1000).all()

        for row_idx, (record, question) in enumerate(records, 2):
            ws_records.cell(row=row_idx, column=1, value=record.id)
            ws_records.cell(row=row_idx, column=2, value=question.question)
            ws_records.cell(row=row_idx, column=3, value=cls.CATEGORY_NAMES.get(question.category, question.category))
            ws_records.cell(row=row_idx, column=4, value=cls.PLATFORM_NAMES.get(record.platform_code, record.platform_code))
            ws_records.cell(row=row_idx, column=5, value="是" if record.mentioned else "否")
            ws_records.cell(row=row_idx, column=6, value=record.rank if record.rank > 0 else "未提及")
            ws_records.cell(row=row_idx, column=7, value=round(record.sentiment, 2))
            ws_records.cell(row=row_idx, column=8, value=record.detect_date)
            ws_records.cell(row=row_idx, column=9, value=record.detect_round)
            ws_records.cell(row=row_idx, column=10, value=record.raw_answer[:500] if record.raw_answer else "")

        if records:
            cls._style_data(ws_records, 2, len(records) + 1, len(headers))
        col_widths = [6, 30, 10, 12, 8, 8, 8, 12, 8, 50]
        for col, width in enumerate(col_widths, 1):
            ws_records.column_dimensions[ws_records.cell(row=1, column=col).column_letter].width = width
        ws_records.freeze_panes = "A2"

        # Sheet3: 问题列表
        ws_questions = wb.create_sheet("监测问题")
        q_headers = ["ID", "问题内容", "分类", "标签", "优先级", "状态"]
        for col, header in enumerate(q_headers, 1):
            ws_questions.cell(row=1, column=col, value=header)
        cls._style_header(ws_questions, 1, len(q_headers))

        questions = db.query(Question).order_by(Question.priority.desc()).all()
        for row_idx, q in enumerate(questions, 2):
            ws_questions.cell(row=row_idx, column=1, value=q.id)
            ws_questions.cell(row=row_idx, column=2, value=q.question)
            ws_questions.cell(row=row_idx, column=3, value=cls.CATEGORY_NAMES.get(q.category, q.category))
            ws_questions.cell(row=row_idx, column=4, value=q.tags)
            ws_questions.cell(row=row_idx, column=5, value=q.priority)
            ws_questions.cell(row=row_idx, column=6, value="启用" if q.status else "禁用")
        if questions:
            cls._style_data(ws_questions, 2, len(questions) + 1, len(q_headers))

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_doctor_report(db: Session, user_id: int) -> bytes:
        """导出医生个人GEO报告（多Sheet）

        Sheet1: 医生Profile
        Sheet2: 语义库列表
        Sheet3: 文章列表
        Sheet4: GEO/AEO监测记录
        """
        from app.models.doctor import DoctorProfile
        from app.models.semantic import Semantic
        from app.models.article import ArticleDraft
        from app.models.monitor import MonitorRecord

        wb = Workbook()

        # Sheet1: 医生Profile
        ws1 = wb.active
        ws1.title = "医生资料"
        ws1.append(["字段", "值"])
        ExportService._style_header(ws1, 1, 2)
        profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
        if profile:
            fields = [
                ("姓名", profile.real_name),
                ("职称", profile.title),
                ("城市", profile.city),
                ("医院", profile.hospital),
                ("科室", profile.department),
                ("专长", profile.specialty),
                ("自我介绍", profile.self_intro_template),
            ]
            for k, v in fields:
                ws1.append([k, v])
        else:
            ws1.append(["未完善医生资料", ""])

        # Sheet2: 语义库
        ws2 = wb.create_sheet("语义库")
        ws2.append(["ID", "语义问题", "分类", "是否启用", "是否付费", "GEO率(%)", "AEO率(%)", "文章数"])
        ExportService._style_header(ws2, 1, 8)
        semantics = db.query(Semantic).filter(Semantic.user_id == user_id).all()
        for s in semantics:
            ws2.append([s.id, s.question, s.category, "是" if s.is_active else "否",
                       "是" if s.is_paid else "否", s.geo_rate, s.aeo_rate, s.article_count])

        # Sheet3: 文章列表
        ws3 = wb.create_sheet("我的文章")
        ws3.append(["ID", "标题", "关联语义ID", "发布平台", "状态", "实体一致", "创建时间"])
        ExportService._style_header(ws3, 1, 7)
        articles = db.query(ArticleDraft).filter(ArticleDraft.user_id == user_id).all()
        platform_names = {"wechat": "微信公众号", "xiaohongshu": "小红书", "zhihu": "知乎",
                         "video": "视频号", "douyin": "抖音", "other": "其他"}
        status_names = {"draft": "草稿", "published": "已发布"}
        for a in articles:
            ws3.append([a.id, a.title, a.semantic_id,
                       platform_names.get(a.platform, a.platform),
                       status_names.get(a.status, a.status),
                       "是" if a.entity_consistent else "否",
                       str(a.created_at) if a.created_at else ""])

        # Sheet4: GEO/AEO监测记录
        ws4 = wb.create_sheet("GEO-AEO监测")
        ws4.append(["ID", "语义ID", "平台", "检测日期", "GEO推荐次数", "AEO引用次数", "AEO置信度"])
        ExportService._style_header(ws4, 1, 7)
        records = db.query(MonitorRecord).filter(
            MonitorRecord.detect_type == "doctor",
            MonitorRecord.semantic_id.in_([s.id for s in semantics]) if semantics else False
        ).all()
        for r in records:
            ws4.append([r.id, r.semantic_id, r.platform_code, r.detect_date,
                       r.recommend_count or 0, r.cite_count or 0, r.aeo_confidence or 0])

        # 调整列宽
        for ws in [ws1, ws2, ws3, ws4]:
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[column].width = min(max_length + 2, 50)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
