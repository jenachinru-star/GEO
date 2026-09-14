import json
import hashlib
import math
from typing import List, Tuple, Optional


class VectorEngine:
    """向量引擎 - 纯Python实现，无外部依赖（SQLite方案，不依赖pgvector/numpy）"""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def text_to_vector(self, text: str) -> List[float]:
        """将文本转换为向量
        基于字符n-gram + 词级哈希的轻量向量，无需外部模型
        """
        if not text or not text.strip():
            return [0.0] * self.dim

        vector = [0.0] * self.dim
        text = text.lower().strip()

        # 字符3-gram
        for i in range(len(text) - 2):
            gram = text[i:i+3]
            hash_val = int(hashlib.md5(gram.encode('utf-8')).hexdigest(), 16)
            idx = hash_val % self.dim
            sign = 1.0 if (hash_val >> 8) % 2 == 0 else -1.0
            vector[idx] += sign

        # 词级（按空格/标点分词）
        import re
        words = re.findall(r'[\w\u4e00-\u9fff]+', text)
        for word in words:
            if len(word) >= 2:
                hash_val = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
                idx = hash_val % self.dim
                sign = 1.0 if (hash_val >> 8) % 2 == 0 else -1.0
                vector[idx] += sign * 2  # 词级权重更高

        # L2归一化
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度（纯Python实现）"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def vector_to_json(self, vector: List[float]) -> str:
        """向量转JSON字符串（存数据库）"""
        return json.dumps(vector)

    def json_to_vector(self, json_str: str) -> List[float]:
        """JSON字符串转向量"""
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except:
            return []

    def find_most_similar(self, query_vec: List[float],
                           candidates: List[Tuple[int, List[float]]],
                           top_k: int = 5,
                           threshold: float = 0.1) -> List[Tuple[int, float]]:
        """从候选中找出最相似的TopK
        candidates: [(id, vector), ...]
        返回: [(id, similarity), ...]
        """
        if not query_vec or not candidates:
            return []

        scored = []
        for cid, cvec in candidates:
            sim = self.cosine_similarity(query_vec, cvec)
            if sim >= threshold:
                scored.append((cid, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# 全局单例
vector_engine = VectorEngine(dim=256)
