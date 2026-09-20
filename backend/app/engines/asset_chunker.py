"""数字资产 - 文本分块引擎

实现父子块分块策略：
- 父块：500-800 token，用于展示上下文
- 子块：128-256 token，用于精准检索
- 按段落/句子边界分割，避免硬切
"""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class AssetChunker:
    """文本分块器"""

    # 分块大小（按字符数估算，中文约1.5字符/token）
    PARENT_CHUNK_SIZE = 1200   # ~800 token
    CHILD_CHUNK_SIZE = 400     # ~256 token
    CHUNK_OVERLAP = 50         # 块间重叠字符

    def chunk_document(self, text: str, title: str = "") -> List[Tuple[str, int]]:
        """将文档分块，返回 (chunk_text, parent_index) 列表

        Args:
            text: 文档全文
            title: 文档标题（加到第一个块）

        Returns:
            [(chunk_text, parent_index), ...]
            parent_index: 父块序号（0-based），第一个块的parent_index=-1表示是父块本身
        """
        if not text or not text.strip():
            return []

        # 1. 按段落分割
        paragraphs = self._split_paragraphs(text)

        # 2. 合并段落成父块
        parent_chunks = self._merge_to_parent_chunks(paragraphs, title)

        # 3. 每个父块再分子块
        all_chunks = []
        for p_idx, parent_text in enumerate(parent_chunks):
            # 父块本身也作为一个检索单元
            all_chunks.append((parent_text, -1))  # parent_index=-1表示父块
            # 子块
            child_chunks = self._split_to_child_chunks(parent_text)
            for child_text in child_chunks:
                all_chunks.append((child_text, p_idx))

        logger.info(f"分块完成: {len(paragraphs)}段 -> {len(parent_chunks)}父块 -> {len(all_chunks)}总块")
        return all_chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        # 按空行分割
        paragraphs = re.split(r'\n\s*\n', text)
        # 过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs

    def _merge_to_parent_chunks(self, paragraphs: List[str], title: str = "") -> List[str]:
        """将小段落合并成目标大小的父块"""
        chunks = []
        current = ""

        # 第一个块加上标题
        if title:
            current = f"【{title}】\n\n"

        for para in paragraphs:
            # 如果当前块加上这个段落不超过大小限制，就合并
            if len(current) + len(para) <= self.PARENT_CHUNK_SIZE:
                current += para + "\n\n"
            else:
                # 当前块已满，保存并开始新块
                if current.strip():
                    chunks.append(current.strip())
                current = para + "\n\n"

        # 保存最后一块
        if current.strip():
            chunks.append(current.strip())

        return chunks

    def _split_to_child_chunks(self, parent_text: str) -> List[str]:
        """将父块分割成更小的子块"""
        if len(parent_text) <= self.CHILD_CHUNK_SIZE:
            return []  # 父块本身就很小，不需要再分

        # 按句子分割
        sentences = re.split(r'(?<=[。！？；\.!?;])\s+', parent_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current = ""

        for sent in sentences:
            if len(current) + len(sent) <= self.CHILD_CHUNK_SIZE:
                current += sent + " "
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = sent + " "

        if current.strip():
            chunks.append(current.strip())

        return chunks


# 全局实例
asset_chunker = AssetChunker()
