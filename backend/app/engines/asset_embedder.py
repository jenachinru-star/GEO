"""数字资产 - Embedding 向量引擎

调用GLM embedding API生成文本向量，用于语义检索。
降级方案：如果API调用失败，自动回退到纯Python n-gram向量。
"""
import json
import logging
from typing import List, Optional
from app.config import settings
from app.engines.vector import vector_engine

logger = logging.getLogger(__name__)


class AssetEmbedder:
    """资产向量化引擎 - 优先使用GLM embedding API，失败时回退到本地向量"""

    # GLM embedding模型名称
    EMBEDDING_MODEL = "embedding-3"  # GLM embedding模型
    EMBEDDING_DIM = 2048  # GLM embedding-3 输出维度

    def __init__(self):
        self._client = None
        self._api_key = settings.GLM_API_KEY
        self._base_url = settings.GLM_BASE_URL

    def _get_client(self):
        """懒加载OpenAI客户端（复用GLM配置）"""
        if self._client is None:
            if not self._api_key or not self._base_url:
                logger.warning("GLM API未配置，embedding将使用本地降级方案")
                return None
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=30,
                )
            except Exception as e:
                logger.error(f"初始化embedding客户端失败: {e}")
                return None
        return self._client

    def embed_text(self, text: str) -> List[float]:
        """将文本转换为向量

        优先使用GLM embedding API，失败时回退到纯Python n-gram向量
        """
        if not text or not text.strip():
            return [0.0] * self.EMBEDDING_DIM

        # 尝试调用GLM embedding API
        client = self._get_client()
        if client:
            try:
                response = client.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=text[:8000],  # 截断超长文本
                )
                vec = response.data[0].embedding
                return vec
            except Exception as e:
                logger.warning(f"GLM embedding API调用失败，回退到本地向量: {e}")

        # 降级：使用纯Python向量
        return vector_engine.text_to_vector(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量向量化"""
        results = []
        for text in texts:
            results.append(self.embed_text(text))
        return results

    def vector_to_json(self, vec: List[float]) -> str:
        """向量转JSON字符串存储"""
        return json.dumps(vec)

    def json_to_vector(self, json_str: str) -> Optional[List[float]]:
        """JSON字符串转回向量"""
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return None

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# 全局实例
asset_embedder = AssetEmbedder()
