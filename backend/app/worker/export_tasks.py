"""资产导出相关任务的处理函数"""
import json
import logging
import os
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.asset import AssetDocument, AssetNote
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def _get_export_dir() -> str:
    """获取导出文件存储目录"""
    export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def handle_asset_export(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理资产导出任务（PDF等耗时格式）"""
    payload = json.loads(task.payload_json or "{}")
    document_id = payload.get("document_id")
    export_format = payload.get("format", "pdf")
    # include_* 参数预留，当前 build_markdown_content 暂不支持选择性导出
    include_summary = payload.get("include_summary", True)
    include_notes = payload.get("include_notes", True)
    include_abstract = payload.get("include_abstract", True)
    user_id = task.created_by

    if not document_id:
        raise ValueError("payload 中缺少 document_id")

    if on_progress:
        on_progress(1, 3, "查询资产文档")

    doc = db.query(AssetDocument).filter(
        AssetDocument.id == document_id, AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise ValueError("资产文档不存在或不属于当前用户")

    notes = db.query(AssetNote).filter(AssetNote.document_id == document_id).all()

    if on_progress:
        on_progress(2, 3, f"生成{export_format.upper()}中")

    # 复用 asset_export.py 中的内容构建函数
    from app.api.asset_export import build_markdown_content, markdown_to_html

    if export_format == "pdf":
        md_content = build_markdown_content(doc, notes)
        html_content = markdown_to_html(md_content, doc.title)
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            # PDF存到文件，返回下载路径
            export_dir = _get_export_dir()
            filename = f"asset_{document_id}_{task.id}.pdf"
            filepath = os.path.join(export_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_bytes)
            if on_progress:
                on_progress(3, 3, "导出完成")
            return {"download_url": f"/api/v1/asset/export/download/{filename}", "filename": filename}
        except ImportError:
            raise ValueError("weasyprint未安装，无法导出PDF")
    elif export_format == "md":
        md_content = build_markdown_content(doc, notes)
        return {"content": md_content, "filename": f"{doc.title}.md"}
    else:
        raise ValueError(f"不支持的导出格式: {export_format}")


register_handler("asset_export", handle_asset_export)
