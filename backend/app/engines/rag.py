from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from app.engines.vector import vector_engine
from app.models import Knowledge
from app.adapters import adapter_factory
from app.config import settings

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG引擎 - 基于知识库的检索增强生成"""

    def __init__(self, db: Session):
        self.db = db

    def search_knowledge(self, query: str, top_k: int = 5,
                         level: str = "public") -> List[Tuple[Knowledge, float]]:
        """语义检索知识库"""
        logger.info(f"RAG检索: query={query[:30]}, level={level}")
        query_vec = vector_engine.text_to_vector(query)

        # 按级别过滤
        level_order = {"public": 0, "internal": 1, "confidential": 2}
        max_level = level_order.get(level, 0)
        allowed_levels = [k for k, v in level_order.items() if v <= max_level]

        knowledge_list = self.db.query(Knowledge).filter(
            Knowledge.status == True,
            Knowledge.level.in_(allowed_levels)
        ).all()

        if not knowledge_list:
            return []

        # 构建候选向量
        candidates = []
        for k in knowledge_list:
            vec = vector_engine.json_to_vector(k.embedding)
            if vec:
                candidates.append((k.id, vec))

        # 相似度检索（阈值设低，因为纯Python向量方法相似度普遍偏低）
        similar = vector_engine.find_most_similar(query_vec, candidates, top_k=top_k, threshold=0.01)

        # 关联回知识库对象
        id_to_knowledge = {k.id: k for k in knowledge_list}
        results = []
        for kid, score in similar:
            if kid in id_to_knowledge:
                results.append((id_to_knowledge[kid], score))

        logger.info(f"RAG检索结果: {len(results)} 条")
        return results

    def generate_answer(self, query: str, platform_code: str = "glm",
                        level: str = "public", history: List[dict] = None) -> Dict:
        """基于知识库生成回答（支持多轮对话）
        Args:
            query: 当前用户问题
            platform_code: AI平台
            level: 知识库级别
            history: 对话历史，格式 [{"role": "user"/"assistant", "content": "..."}]
        """
        # 1. 检索知识库（结合历史上下文优化查询）
        search_query = query
        if history:
            # 简单的query改写：把最近一轮的上下文加进去
            recent = history[-2:] if len(history) >= 2 else history
            context_text = " ".join([h.get("content", "") for h in recent])
            search_query = f"{context_text} {query}"

        relevant = self.search_knowledge(search_query, top_k=5, level=level)

        # 2. 构建上下文
        context_parts = []
        for k, score in relevant:
            context_parts.append(f"【{k.title}】(相关度:{score:.2f})\n{k.content}")

        context = "\n\n".join(context_parts) if context_parts else "暂无相关知识库内容"

        # 3. 构建历史对话文本
        history_text = ""
        if history:
            history_lines = []
            for h in history[-6:]:  # 只保留最近6轮，避免token过长
                role = "用户" if h.get("role") == "user" else "助手"
                history_lines.append(f"{role}: {h.get('content', '')}")
            history_text = "\n".join(history_lines)

        # 4. 构建system_prompt
        system_prompt = f"""你是登麟科技的官方智能助手。请基于以下知识库内容回答用户问题。
要求：
1. 只使用知识库中提供的信息，不要编造
2. 如果知识库中没有相关信息，请如实告知
3. 回答简洁专业，符合生物科技行业的表述规范
4. 公司全称：登麟科技（原层次智慧）
5. 结合对话历史理解用户当前问题的上下文

知识库内容：
{context}

对话历史：
{history_text if history_text else "（无历史对话）"}
"""

        # 5. 调用大模型
        adapter = adapter_factory.get_adapter(platform_code)
        if not adapter:
            adapter = adapter_factory.get_adapter(adapter_factory.get_enabled_platforms()[0])

        if not adapter:
            return {
                "answer": "未配置可用的AI平台",
                "sources": [],
                "platform": "none"
            }

        # 临时修改temperature为0.7用于问答
        original_temp = adapter.temperature
        adapter.temperature = 0.7
        result = adapter.query(query, system_prompt=system_prompt)
        adapter.temperature = original_temp

        return {
            "answer": result.answer if result.success else f"生成失败: {result.error}",
            "sources": [{"id": k.id, "title": k.title, "score": float(score)} for k, score in relevant],
            "platform": platform_code,
            "success": result.success
        }

    def update_knowledge_embedding(self, knowledge_id: int):
        """更新知识库条目的向量"""
        k = self.db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if not k:
            return
        text = f"{k.title} {k.content}"
        vec = vector_engine.text_to_vector(text)
        k.embedding = vector_engine.vector_to_json(vec)
        self.db.commit()

    def rebuild_all_embeddings(self):
        """重建所有知识库条目的向量"""
        knowledge_list = self.db.query(Knowledge).all()
        for k in knowledge_list:
            text = f"{k.title} {k.content}"
            vec = vector_engine.text_to_vector(text)
            k.embedding = vector_engine.vector_to_json(vec)
        self.db.commit()
        return len(knowledge_list)
