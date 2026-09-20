"""数字资产 - 文件解析引擎

支持的文件格式：
- TXT / Markdown（直接读取）
- PDF（预留，需安装 pypdf）
- Word（预留，需安装 python-docx）

第一阶段优先支持文本类文件，PDF/Word后续扩展。
"""
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AssetParser:
    """文件内容解析器"""

    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown', '.text'}
    PDF_EXTENSIONS = {'.pdf'}
    DOCX_EXTENSIONS = {'.docx', '.doc'}

    def parse_file(self, file_path: str, file_name: str = "") -> Dict:
        """解析文件，返回结构化结果

        Returns:
            {
                "title": str,
                "content": str,
                "success": bool,
                "error": str,
            }
        """
        ext = os.path.splitext(file_name or file_path)[1].lower()

        try:
            if ext in self.SUPPORTED_EXTENSIONS:
                return self._parse_text(file_path, file_name)
            elif ext in self.PDF_EXTENSIONS:
                return self._parse_pdf(file_path, file_name)
            elif ext in self.DOCX_EXTENSIONS:
                return self._parse_docx(file_path, file_name)
            else:
                return {
                    "success": False,
                    "error": f"不支持的文件格式: {ext}，当前支持TXT/MD文件"
                }
        except Exception as e:
            logger.error(f"文件解析失败: {e}")
            return {"success": False, "error": f"文件解析失败: {str(e)[:200]}"}

    def _parse_text(self, file_path: str, file_name: str) -> Dict:
        """解析纯文本文件"""
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        content = ""

        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if not content:
            return {"success": False, "error": "无法读取文件内容"}

        # 从文件名提取标题
        title = os.path.splitext(file_name)[0]

        return {
            "success": True,
            "title": title,
            "content": content,
            "error": "",
        }

    def _parse_pdf(self, file_path: str, file_name: str) -> Dict:
        """解析PDF文件（需安装 pypdf）"""
        try:
            from pypdf import PdfReader
        except ImportError:
            return {
                "success": False,
                "error": "PDF解析需要安装pypdf库，请运行: pip install pypdf"
            }

        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")

        content = "\n\n".join(text_parts)
        title = os.path.splitext(file_name)[0]

        return {
            "success": True,
            "title": title,
            "content": content,
            "error": "",
        }

    def _parse_docx(self, file_path: str, file_name: str) -> Dict:
        """解析Word文件（需安装 python-docx）"""
        try:
            from docx import Document
        except ImportError:
            return {
                "success": False,
                "error": "Word解析需要安装python-docx库，请运行: pip install python-docx"
            }

        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        content = "\n\n".join(paragraphs)
        title = os.path.splitext(file_name)[0]

        return {
            "success": True,
            "title": title,
            "content": content,
            "error": "",
        }


# 全局实例
asset_parser = AssetParser()
