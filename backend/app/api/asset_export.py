"""数字资产 - 内容导出 API

支持导出格式：
- Markdown (.md)
- HTML (.html)
- PDF (.pdf)
- 思维导图 (.mm.md)
- Excel (.xlsx)
- PPT (.pptx)

导出内容：总结 + 原文摘要 + 笔记
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetDocument, AssetNote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset/export", tags=["数字资产-导出"])


# ============ 请求模型 ============

class ExportRequest(BaseModel):
    document_id: int
    format: str  # md / html / pdf
    include_summary: bool = True
    include_notes: bool = True
    include_abstract: bool = True


# ============ 导出内容生成 ============

def build_markdown_content(doc: AssetDocument, notes: list) -> str:
    """构建Markdown格式的导出内容"""
    lines = []

    # 标题
    lines.append(f"# {doc.title}")
    lines.append("")

    # 元信息
    lines.append(f"**来源：** {doc.source_type}")
    if doc.author:
        lines.append(f"**作者：** {doc.author}")
    if doc.publish_date:
        lines.append(f"**发布日期：** {doc.publish_date}")
    lines.append(f"**导出时间：** {doc.updated_at.strftime('%Y-%m-%d %H:%M') if doc.updated_at else ''}")
    lines.append("")

    # 原文摘要
    if doc.summary and len(doc.summary) > 50:
        lines.append("## 原文摘要")
        lines.append("")
        lines.append(doc.summary[:1000])
        lines.append("")

    # AI总结
    if doc.ai_summary:
        lines.append("## AI总结")
        lines.append("")
        lines.append(doc.ai_summary)
        lines.append("")

    # 笔记
    if notes:
        lines.append("## 我的笔记")
        lines.append("")
        for note in notes:
            lines.append(f"### {note.title or '笔记'}")
            lines.append("")
            lines.append(note.content)
            lines.append("")

    # 标签
    if doc.tags:
        lines.append("---")
        lines.append(f"**标签：** {doc.tags}")

    return "\n".join(lines)


def markdown_to_html(md_content: str, title: str) -> str:
    """简单的Markdown转HTML（带样式）"""
    # 简单的Markdown→HTML转换，不引入完整库，够用就行
    import re

    html = md_content

    # 标题
    html = re.sub(r'^# (.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # 粗体
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

    # 换行→段落
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    for p in paragraphs:
        if p.startswith('<h') or p.startswith('<hr') or p.startswith('---'):
            html_paragraphs.append(p)
        else:
            lines = p.split('\n')
            html_lines = [f'<p>{line}</p>' for line in lines if line.strip()]
            html_paragraphs.append('\n'.join(html_lines))

    body = '\n'.join(html_paragraphs)

    # 完整HTML包装
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            line-height: 1.8;
            color: #333;
        }}
        h1 {{
            color: #1a1a1a;
            border-bottom: 2px solid #e5e5e5;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
        }}
        p {{
            margin: 12px 0;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 30px 0;
        }}
        strong {{
            color: #1a1a1a;
        }}
    </style>
</head>
<body>
{body}
</body>
</html>"""

    return full_html


# ============ 导出接口 ============

@router.post("/document", summary="导出单篇文档为指定格式")
def export_document(
    req: ExportRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出单篇文档为Markdown/HTML/PDF"""
    doc = db.query(AssetDocument).filter(
        AssetDocument.id == req.document_id,
        AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 获取笔记
    notes = db.query(AssetNote).filter(
        AssetNote.document_id == doc.id,
        AssetNote.user_id == user_id
    ).order_by(AssetNote.updated_at.desc()).all()

    # 构建Markdown内容
    md_content = build_markdown_content(doc, notes)

    # 文件名
    filename = doc.title[:50].replace('/', '_').replace('\\', '_')

    if req.format == "md":
        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}.md"}
        )

    elif req.format == "html":
        html_content = markdown_to_html(md_content, doc.title)
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}.html"}
        )

    elif req.format == "pdf":
        # PDF导出：尝试用WeasyPrint，如果没装就降级到HTML下载
        try:
            from weasyprint import HTML
            html_content = markdown_to_html(md_content, doc.title)
            pdf_bytes = HTML(string=html_content).write_pdf()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}.pdf"}
            )
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF导出功能未配置，请先安装weasyprint，或使用HTML格式导出后浏览器打印为PDF"
            )

    elif req.format == "mindmap":
        # 思维导图：Markmap格式（用Markdown层级结构生成思维导图）
        mindmap_content = f"""---
title: {doc.title}
markmap:
  colorFreezeLevel: 2
---

# {doc.title}

## 基本信息
- 来源: {doc.source_type}
- 作者: {doc.author or '未知'}
- 日期: {doc.publish_date or '未知'}

## 原文摘要
{doc.summary[:500] if doc.summary else '无'}

## AI总结
{doc.ai_summary[:800] if doc.ai_summary else '无'}

## 我的笔记
{chr(10).join([f'- {n.title or "笔记"}: {n.content[:200]}' for n in notes]) if notes else '- 无'}

## 标签
{doc.tags or '无'}
"""
        return Response(
            content=mindmap_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}_mindmap.md"}
        )

    elif req.format == "excel":
        # Excel导出：用openpyxl
        try:
            from openpyxl import Workbook
            from io import BytesIO

            wb = Workbook()
            ws = wb.active
            ws.title = "文献列表"

            # 表头
            ws.append(["标题", "作者", "来源", "发布日期", "摘要", "总结", "标签"])
            ws.append([
                doc.title,
                doc.author or "",
                doc.source_type,
                doc.publish_date or "",
                (doc.summary or "")[:500],
                (doc.ai_summary or "")[:1000],
                doc.tags or "",
            ])

            # 调整列宽
            ws.column_dimensions['A'].width = 50
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['E'].width = 80
            ws.column_dimensions['F'].width = 100

            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            return Response(
                content=buffer.read(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}.xlsx"}
            )
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="Excel导出功能未配置，请先安装openpyxl"
            )

    elif req.format == "ppt":
        # PPT导出：用python-pptx
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from io import BytesIO

            prs = Presentation()

            # 封面
            slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(slide_layout)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            title.text = doc.title
            subtitle.text = f"导出时间: {datetime.now().strftime('%Y-%m-%d')}"

            # 摘要页
            if doc.summary:
                slide_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(slide_layout)
                slide.shapes.title.text = "原文摘要"
                content = slide.placeholders[1]
                content.text = doc.summary[:1000]

            # AI总结页
            if doc.ai_summary:
                slide_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(slide_layout)
                slide.shapes.title.text = "AI总结"
                content = slide.placeholders[1]
                content.text = doc.ai_summary[:1500]

            # 笔记页
            if notes:
                slide_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(slide_layout)
                slide.shapes.title.text = "我的笔记"
                content = slide.placeholders[1]
                content.text = "\n\n".join([f"{n.title or '笔记'}: {n.content[:300]}" for n in notes])

            buffer = BytesIO()
            prs.save(buffer)
            buffer.seek(0)

            return Response(
                content=buffer.read(),
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}.pptx"}
            )
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PPT导出功能未配置，请先安装python-pptx"
            )

    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式")


@router.post("/preview", summary="预览导出内容（不下载）")
def preview_export(
    req: ExportRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """预览导出内容"""
    doc = db.query(AssetDocument).filter(
        AssetDocument.id == req.document_id,
        AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    notes = db.query(AssetNote).filter(
        AssetNote.document_id == doc.id,
        AssetNote.user_id == user_id
    ).order_by(AssetNote.updated_at.desc()).all()

    md_content = build_markdown_content(doc, notes)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "content": md_content,
            "title": doc.title,
        }
    }
