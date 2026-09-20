"""数字资产 - 语义搜索与个人RAG API

提供：
- 资产库语义搜索：基于chunk级别的向量检索
- 个人知识库问答：基于chunk级别的RAG问答（更精准）
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetDocument, AssetChunk
from app.engines.asset_embedder import asset_embedder
from app.adapters import adapter_factory
from app.usage_context import usage_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset", tags=["数字资产-搜索"])


# ============ 请求体模型 ============

class RagQueryRequest(BaseModel):
    question: str
    platform: str = "glm"
    top_k: int = 5
    history: Optional[List[dict]] = None


# ============ 语义搜索 ============

@router.get("/search", summary="语义搜索资产库")
def search_assets(
    q: str = Query(..., description="搜索关键词"),
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """在用户的资产库中做语义搜索（基于chunk级别检索）"""
    if not q.strip():
        return {"code": 0, "message": "success", "data": {"items": []}}

    # 生成查询向量
    query_vec = asset_embedder.embed_text(q)

    # 获取用户所有有向量的chunks
    chunks = db.query(AssetChunk).filter(
        AssetChunk.user_id == user_id,
        AssetChunk.embedding != "",
    ).all()

    if not chunks:
        # 降级：如果没有chunks，用文档级搜索
        return _fallback_document_search(db, user_id, q, top_k)

    # 计算每个chunk的相似度
    chunk_scores = []
    for chunk in chunks:
        chunk_vec = asset_embedder.json_to_vector(chunk.embedding)
        if not chunk_vec:
            continue
        score = asset_embedder.cosine_similarity(query_vec, chunk_vec)
        chunk_scores.append((chunk, score))

    # 按相似度排序
    chunk_scores.sort(key=lambda x: x[1], reverse=True)

    # 取top_k个chunk，关联回document，去重
    doc_seen = set()
    items = []
    for chunk, score in chunk_scores[:top_k * 2]:  # 多取一些用于去重
        if chunk.document_id in doc_seen:
            continue
        doc_seen.add(chunk.document_id)

        doc = db.query(AssetDocument).filter(AssetDocument.id == chunk.document_id).first()
        if not doc:
            continue

        items.append({
            "id": doc.id,
            "title": doc.title,
            "summary": doc.summary[:200] if doc.summary else chunk.content[:200],
            "score": float(score),
            "category": doc.category,
            "tags": doc.tags,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })

        if len(items) >= top_k:
            break

    return {"code": 0, "message": "success", "data": {"items": items}}


def _fallback_document_search(db: Session, user_id: int, q: str, top_k: int) -> dict:
    """降级方案：文档级搜索（没有chunks时使用）"""
    from app.engines.vector import vector_engine

    docs = db.query(AssetDocument).filter(
        AssetDocument.user_id == user_id,
        AssetDocument.content != ""
    ).all()

    if not docs:
        return {"items": []}

    query_vec = vector_engine.text_to_vector(q)
    candidates = []
    for doc in docs:
        text = f"{doc.title} {doc.content[:500]}"
        vec = vector_engine.text_to_vector(text)
        candidates.append((doc.id, vec))

    similar = vector_engine.find_most_similar(query_vec, candidates, top_k=top_k, threshold=0.01)

    id_to_doc = {d.id: d for d in docs}
    items = []
    for doc_id, score in similar:
        if doc_id in id_to_doc:
            doc = id_to_doc[doc_id]
            items.append({
                "id": doc.id,
                "title": doc.title,
                "summary": doc.summary[:200] if doc.summary else "",
                "score": float(score),
                "category": doc.category,
                "tags": doc.tags,
            })

    return {"items": items}


# ============ 个人RAG问答 ============

@router.post("/rag", summary="个人知识库问答")
def rag_answer(
    req: RagQueryRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """基于用户自己的资产库进行RAG问答（chunk级精准检索）"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 1. 生成查询向量
    query_vec = asset_embedder.embed_text(req.question)

    # 2. 检索最相关的chunks
    chunks = db.query(AssetChunk).filter(
        AssetChunk.user_id == user_id,
        AssetChunk.embedding != "",
    ).all()

    if not chunks:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "answer": "您的知识库还是空的，先收藏一些文章或文献吧。",
                "sources": [],
            }
        }

    # 计算相似度
    chunk_scores = []
    for chunk in chunks:
        chunk_vec = asset_embedder.json_to_vector(chunk.embedding)
        if not chunk_vec:
            continue
        score = asset_embedder.cosine_similarity(query_vec, chunk_vec)
        chunk_scores.append((chunk, score))

    chunk_scores.sort(key=lambda x: x[1], reverse=True)

    # 3. 构建上下文（用最相关的chunks）
    context_parts = []
    sources = []
    seen_docs = set()

    for chunk, score in chunk_scores[:req.top_k * 2]:
        # 每个文档只取最相关的1-2个chunk
        doc_count = sum(1 for s in sources if s["id"] == chunk.document_id)
        if doc_count >= 2:
            continue

        doc = db.query(AssetDocument).filter(AssetDocument.id == chunk.document_id).first()
        if not doc:
            continue

        context_parts.append(f"【{doc.title}】(相关度:{score:.2f})\n{chunk.content}")

        if chunk.document_id not in seen_docs:
            seen_docs.add(chunk.document_id)
            sources.append({
                "id": doc.id,
                "title": doc.title,
                "score": float(score),
            })

        if len(context_parts) >= req.top_k:
            break

    context = "\n\n".join(context_parts) if context_parts else "暂无相关内容"

    # 4. 构建对话历史
    history_text = ""
    if req.history:
        history_lines = []
        for h in req.history[-6:]:
            role = "用户" if h.get("role") == "user" else "助手"
            history_lines.append(f"{role}: {h.get('content', '')}")
        history_text = "\n".join(history_lines)

    # 5. 构建system_prompt
    system_prompt = f"""你是一位专业的医学知识助手。请基于用户的个人知识库内容回答问题。

要求：
1. 主要使用知识库中提供的信息回答，不要编造
2. 如果知识库中没有相关信息，可以基于你的专业知识补充，但要明确标注"（知识库中未找到相关内容，以下为通用知识）"
3. 回答要专业、准确、简洁
4. 结合对话历史理解用户当前问题的上下文

知识库内容：
{context}

对话历史：
{history_text if history_text else "（无历史对话）"}
"""

    # 6. 调用AI
    adapter = adapter_factory.get_adapter(req.platform)
    if not adapter:
        enabled = adapter_factory.get_enabled_platforms()
        if not enabled:
            raise HTTPException(status_code=400, detail="未配置可用的AI平台")
        adapter = adapter_factory.get_adapter(enabled[0])
        req.platform = enabled[0]

    ctx_token = usage_context.set(
        user_id=user_id,
        task_type="asset_rag",
        ref_id=0,
        ref_type="query",
        source="http"
    )

    try:
        result = adapter.query(
            req.question,
            system_prompt=system_prompt,
            usage_ctx={"task_type": "asset_rag", "source": "http"}
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=f"AI回答失败: {result.error}")

        return {
            "code": 0,
            "message": "success",
            "data": {
                "answer": result.answer,
                "sources": sources,
                "platform": req.platform,
                "tokens_input": result.tokens_input,
                "tokens_output": result.tokens_output,
            }
        }
    finally:
        usage_context.reset(ctx_token)
