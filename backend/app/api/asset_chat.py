"""数字资产 - 多模型对话 API

功能：
- 对话会话管理（CRUD）
- 多模型对话（支持切换8个国产大模型）
- RAG增强问答（基于用户知识库检索）
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetChatSession, AssetChatMessage, AssetChunk, AssetDocument
from app.engines.asset_embedder import asset_embedder
from app.adapters import adapter_factory
from app.usage_context import usage_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset", tags=["数字资产-对话"])


# ============ 助手模板定义 ============

ASSISTANT_TEMPLATES = {
    "auto": {
        "name": "自动模式",
        "description": "AI自动判断最合适的回答方式",
        "icon": "🤖",
    },
    "general": {
        "name": "通用问答",
        "description": "自由对话，基于知识库回答问题",
        "icon": "💬",
        "system_addon": ""
    },
    "literature": {
        "name": "文献精读",
        "description": "按IMRAD结构解析论文：背景/方法/结果/结论",
        "icon": "📚",
        "system_addon": """
【你当前处于"文献精读"模式】
请按以下结构解析文献：
1. **研究背景与问题**：这篇论文要解决什么问题？
2. **研究方法**：研究设计、样本量、干预措施、对照
3. **主要结果**：关键数据、统计学结果
4. **研究结论**：作者得出了什么结论？
5. **局限性**：研究有哪些不足？
6. **临床意义**：这篇研究对临床实践有什么指导价值？

要求：用结构化的方式呈现，重点突出数据和临床价值。
"""
    },
    "clinical": {
        "name": "临床决策",
        "description": "按CARDS框架分析病例：诊断/检查/治疗/风险",
        "icon": "🏥",
        "system_addon": """
【你当前处于"临床决策助手"模式】
请按以下结构分析病例：
1. **关键信息提取**：患者年龄、主诉、现病史、既往史、检查结果
2. **鉴别诊断**：按可能性排序，列出主要鉴别诊断及依据
3. **建议检查**：为明确诊断还需要做哪些检查？
4. **治疗方案**：推荐的治疗方案及理由
5. **风险提示**：需要注意的风险、并发症、禁忌证
6. **下一步建议**：建议的随访、监测指标

要求：
- 基于循证医学证据
- 区分"明确建议"和"仅供参考"
- 最后加上免责声明：本回答仅供参考，具体诊疗请结合临床实际
"""
    },
    "popularize": {
        "name": "科普创作",
        "description": "把专业内容改写成患者能懂的科普文章",
        "icon": "✍️",
        "system_addon": """
【你当前处于"科普创作"模式】
请把专业医学内容改写成患者能看懂的科普文章：
1. 用通俗易懂的语言，避免专业术语（必须用的术语要解释清楚）
2. 结构清晰：开头引入→正文分点→结尾总结
3. 语气亲切，像医生在跟患者聊天
4. 不要有绝对化表述（如"百分百治愈"、"最好的药"等）
5. 不要推荐具体药物剂量
6. 保留核心医学事实，不要编造
7. 800-1500字左右
"""
    },
}


async def detect_template(message: str) -> str:
    """根据用户输入自动识别最合适的模板"""
    msg = message.lower()

    # 关键词匹配
    literature_keywords = ["文献", "论文", "研究", "摘要", "文章", "paper", "study", "这篇文章", "这篇文献"]
    clinical_keywords = ["病例", "患者", "诊断", "治疗", "用药", "临床", "鉴别", "检查", "病例分析", "病人"]
    popularize_keywords = ["科普", "通俗", "患者", "老百姓", "大众", "写成文章", "公众号"]

    # 计算各模板匹配分数
    scores = {
        "literature": sum(1 for k in literature_keywords if k in msg),
        "clinical": sum(1 for k in clinical_keywords if k in msg),
        "popularize": sum(1 for k in popularize_keywords if k in msg),
    }

    # 取最高分的
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return "general"


# ============ 请求体模型 ============

class ChatSendRequest(BaseModel):
    session_id: Optional[int] = None  # 不传则创建新会话
    document_id: Optional[int] = None  # 关联的文档（可选）
    message: str
    platform: str = "glm"  # glm / minimax / deepseek / doubao / qwen / kimi / ernie / yuanbao
    top_k: int = 5
    template: str = "auto"  # auto / general / literature / clinical / popularize


# ============ 模型列表 ============

@router.get("/chat/models", summary="获取可用模型列表")
def get_available_models(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """返回当前系统已配置的所有AI模型"""
    enabled = adapter_factory.get_enabled_platforms()

    # 模型元信息
    model_info = {
        "glm": {"name": "智谱GLM", "description": "性价比高，响应快", "color": "blue"},
        "minimax": {"name": "MiniMax", "description": "高速长文本，适合文献", "color": "green"},
        "deepseek": {"name": "DeepSeek", "description": "推理能力强，适合复杂问题", "color": "purple"},
        "doubao": {"name": "豆包", "description": "字节跳动，中文理解好", "color": "orange"},
        "qwen": {"name": "通义千问", "description": "阿里，医疗场景优化", "color": "cyan"},
        "kimi": {"name": "Kimi", "description": "月之暗面，长文本处理", "color": "magenta"},
        "ernie": {"name": "文心一言", "description": "百度，知识丰富", "color": "red"},
        "yuanbao": {"name": "腾讯元宝", "description": "腾讯混元，稳定可靠", "color": "geekblue"},
    }

    models = []
    for platform in enabled:
        info = model_info.get(platform, {"name": platform, "description": "", "color": "default"})
        adapter = adapter_factory.get_adapter(platform)
        models.append({
            "code": platform,
            "name": info["name"],
            "description": info["description"],
            "color": info["color"],
            "model": getattr(adapter, 'model', ''),
        })

    return {"code": 0, "message": "success", "data": {"models": models}}


@router.get("/chat/templates", summary="获取助手模板列表")
def get_templates():
    """返回所有可用的助手模板"""
    templates = []
    for key, tpl in ASSISTANT_TEMPLATES.items():
        templates.append({
            "key": key,
            "name": tpl["name"],
            "description": tpl["description"],
            "icon": tpl["icon"],
        })
    return {"code": 0, "message": "success", "data": {"templates": templates}}


# ============ 会话管理 ============

@router.get("/chat/sessions", summary="获取对话会话列表")
def list_sessions(
    document_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取用户的对话会话列表，支持关键词搜索"""
    query = db.query(AssetChatSession).filter(AssetChatSession.user_id == user_id)
    if document_id:
        query = query.filter(AssetChatSession.document_id == document_id)

    # 关键词搜索（按标题模糊匹配）
    if keyword:
        query = query.filter(AssetChatSession.title.like(f"%{keyword}%"))

    sessions = query.order_by(AssetChatSession.updated_at.desc()).all()

    items = [{
        "id": s.id,
        "title": s.title,
        "platform": s.platform,
        "document_id": s.document_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    } for s in sessions]

    return {"code": 0, "message": "success", "data": {"items": items}}


@router.post("/chat/sessions", summary="创建对话会话")
def create_session(
    document_id: Optional[int] = None,
    platform: str = "glm",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """创建新的对话会话"""
    session = AssetChatSession(
        user_id=user_id,
        document_id=document_id,
        platform=platform,
        title="新对话",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {"code": 0, "message": "success", "data": {
        "id": session.id,
        "title": session.title,
        "platform": session.platform,
    }}


@router.get("/chat/sessions/{session_id}/messages", summary="获取会话消息历史")
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取会话的所有消息"""
    session = db.query(AssetChatSession).filter(
        AssetChatSession.id == session_id,
        AssetChatSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.query(AssetChatMessage).filter(
        AssetChatMessage.session_id == session_id
    ).order_by(AssetChatMessage.created_at.asc()).all()

    items = [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "platform": m.platform,
        "model": m.model,
        "sources": json.loads(m.sources) if m.sources else [],
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in messages]

    return {"code": 0, "message": "success", "data": {
        "session": {
            "id": session.id,
            "title": session.title,
            "platform": session.platform,
            "document_id": session.document_id,
        },
        "messages": items,
    }}


@router.delete("/chat/sessions/{session_id}", summary="删除对话会话")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除对话会话及其所有消息"""
    session = db.query(AssetChatSession).filter(
        AssetChatSession.id == session_id,
        AssetChatSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.delete(session)
    db.commit()
    return {"code": 0, "message": "success"}


@router.put("/chat/sessions/{session_id}", summary="重命名会话")
def rename_session(
    session_id: int,
    title: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """重命名对话会话"""
    if not title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")

    session = db.query(AssetChatSession).filter(
        AssetChatSession.id == session_id,
        AssetChatSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    session.title = title.strip()[:200]
    db.commit()
    return {"code": 0, "message": "success", "data": {"title": session.title}}


# ============ 发送消息（核心） ============

@router.post("/chat/send", summary="发送消息（多模型对话）")
def send_message(
    req: ChatSendRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """发送消息并获取AI回复（支持多模型切换）"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 1. 获取或创建会话
    if req.session_id:
        session = db.query(AssetChatSession).filter(
            AssetChatSession.id == req.session_id,
            AssetChatSession.user_id == user_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        # 更新会话使用的模型
        session.platform = req.platform
    else:
        session = AssetChatSession(
            user_id=user_id,
            document_id=req.document_id,
            platform=req.platform,
            title=req.message[:30] + "..." if len(req.message) > 30 else req.message,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. 保存用户消息
    user_msg = AssetChatMessage(
        session_id=session.id,
        user_id=user_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    db.commit()

    # 3. RAG检索相关知识
    query_vec = asset_embedder.embed_text(req.message)

    # 确定检索范围：如果指定了文档，只检索该文档；否则检索用户全部知识库
    chunk_query = db.query(AssetChunk).filter(
        AssetChunk.user_id == user_id,
        AssetChunk.embedding != "",
    )
    if req.document_id:
        chunk_query = chunk_query.filter(AssetChunk.document_id == req.document_id)

    chunks = chunk_query.all()

    context_parts = []
    sources = []
    if chunks:
        # 计算相似度
        chunk_scores = []
        for chunk in chunks:
            chunk_vec = asset_embedder.json_to_vector(chunk.embedding)
            if not chunk_vec:
                continue
            score = asset_embedder.cosine_similarity(query_vec, chunk_vec)
            chunk_scores.append((chunk, score))

        chunk_scores.sort(key=lambda x: x[1], reverse=True)

        # 取top_k个chunk
        seen_docs = set()
        for chunk, score in chunk_scores[:req.top_k * 2]:
            doc = db.query(AssetDocument).filter(AssetDocument.id == chunk.document_id).first()
            if not doc:
                continue

            context_parts.append(f"【{doc.title}】\n{chunk.content}")

            if doc.id not in seen_docs:
                seen_docs.add(doc.id)
                sources.append({
                    "id": doc.id,
                    "title": doc.title,
                    "score": float(score),
                })

            if len(context_parts) >= req.top_k:
                break

    context = "\n\n".join(context_parts) if context_parts else "（知识库中未找到相关内容）"

    # 4. 获取对话历史（最近10轮）
    recent_messages = db.query(AssetChatMessage).filter(
        AssetChatMessage.session_id == session.id,
        AssetChatMessage.id != user_msg.id,
    ).order_by(AssetChatMessage.created_at.desc()).limit(20).all()
    recent_messages.reverse()

    history_lines = []
    for m in recent_messages:
        role = "用户" if m.role == "user" else "助手"
        history_lines.append(f"{role}: {m.content}")
    history_text = "\n".join(history_lines[-10:]) if history_lines else ""

    # 5. 确定使用的模板
    template_key = req.template
    if template_key == "auto":
        # 自动识别模板
        import asyncio
        try:
            template_key = asyncio.run(detect_template(req.message))
        except:
            template_key = "general"

    template_info = ASSISTANT_TEMPLATES.get(template_key, ASSISTANT_TEMPLATES["general"])
    template_addon = template_info.get("system_addon", "")

    # 6. 构建system_prompt
    system_prompt = f"""你是一位专业的医学知识助手。请基于用户的个人知识库内容回答问题。

{template_addon}

要求：
1. 主要使用知识库中提供的信息回答，不要编造
2. 如果知识库中没有相关信息，可以基于你的专业知识补充，但要明确标注"（知识库中未找到相关内容，以下为通用知识）"
3. 回答要专业、准确、简洁，符合医疗行业规范
4. 结合对话历史理解用户当前问题的上下文

知识库内容：
{context}

对话历史：
{history_text if history_text else "（无历史对话）"}
"""

    # 6. 调用AI模型
    adapter = adapter_factory.get_adapter(req.platform)
    if not adapter:
        enabled = adapter_factory.get_enabled_platforms()
        if not enabled:
            raise HTTPException(status_code=400, detail="未配置可用的AI模型")
        adapter = adapter_factory.get_adapter(enabled[0])
        req.platform = enabled[0]

    ctx_token = usage_context.set(
        user_id=user_id,
        task_type="asset_chat",
        ref_id=session.id,
        ref_type="chat_session",
        source="http"
    )

    try:
        result = adapter.query(
            req.message,
            system_prompt=system_prompt,
            usage_ctx={"task_type": "asset_chat", "source": "http"}
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=f"AI回答失败: {result.error}")

        # 7. 保存AI回复
        assistant_msg = AssetChatMessage(
            session_id=session.id,
            user_id=user_id,
            role="assistant",
            content=result.answer,
            platform=req.platform,
            model=getattr(adapter, 'model', ''),
            tokens_input=result.tokens_input or 0,
            tokens_output=result.tokens_output or 0,
            sources=json.dumps(sources, ensure_ascii=False),
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # 更新会话时间
        session.updated_at = __import__('datetime').datetime.now()
        db.commit()

        return {
            "code": 0,
            "message": "success",
            "data": {
                "session_id": session.id,
                "message": {
                    "id": assistant_msg.id,
                    "role": "assistant",
                    "content": result.answer,
                    "platform": req.platform,
                    "model": assistant_msg.model,
                    "sources": sources,
                }
            }
        }

    finally:
        usage_context.reset(ctx_token)


# ============ 多模型并行对比 ============

class ChatCompareRequest(BaseModel):
    message: str
    platforms: List[str] = []  # 要对比的模型列表，最多3个
    document_id: Optional[int] = None
    top_k: int = 5


@router.post("/chat/compare", summary="多模型并行对比")
def compare_models(
    req: ChatCompareRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """同时调用多个模型回答同一个问题，并排对比结果"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    if not req.platforms or len(req.platforms) == 0:
        raise HTTPException(status_code=400, detail="请至少选择一个模型")

    if len(req.platforms) > 3:
        raise HTTPException(status_code=400, detail="最多同时对比3个模型")

    # 1. RAG检索相关知识（和单模型对话一样）
    query_vec = asset_embedder.embed_text(req.message)
    chunk_query = db.query(AssetChunk).filter(
        AssetChunk.user_id == user_id,
        AssetChunk.embedding != "",
    )
    if req.document_id:
        chunk_query = chunk_query.filter(AssetChunk.document_id == req.document_id)

    chunks = chunk_query.all()

    context_parts = []
    sources = []
    if chunks:
        chunk_scores = []
        for chunk in chunks:
            chunk_vec = asset_embedder.json_to_vector(chunk.embedding)
            if not chunk_vec:
                continue
            score = asset_embedder.cosine_similarity(query_vec, chunk_vec)
            chunk_scores.append((chunk, score))

        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        seen_docs = set()
        for chunk, score in chunk_scores[:req.top_k * 2]:
            doc = db.query(AssetDocument).filter(AssetDocument.id == chunk.document_id).first()
            if not doc:
                continue
            context_parts.append(f"【{doc.title}】\n{chunk.content}")
            if doc.id not in seen_docs:
                seen_docs.add(doc.id)
                sources.append({"id": doc.id, "title": doc.title, "score": float(score)})
            if len(context_parts) >= req.top_k:
                break

    context = "\n\n".join(context_parts) if context_parts else "（知识库中未找到相关内容）"

    # 2. 构建system_prompt
    system_prompt = f"""你是一位专业的医学知识助手。请基于用户的个人知识库内容回答问题。

要求：
1. 主要使用知识库中提供的信息回答，不要编造
2. 如果知识库中没有相关信息，可以基于你的专业知识补充，但要明确标注"（知识库中未找到相关内容，以下为通用知识）"
3. 回答要专业、准确、简洁，符合医疗行业规范

知识库内容：
{context}
"""

    # 3. 并行调用多个模型
    results = []
    for platform in req.platforms:
        adapter = adapter_factory.get_adapter(platform)
        if not adapter:
            results.append({
                "platform": platform,
                "success": False,
                "error": "模型未配置",
                "content": "",
            })
            continue

        try:
            result = adapter.query(
                req.message,
                system_prompt=system_prompt,
                usage_ctx={"task_type": "asset_chat_compare", "source": "http"}
            )

            if result.success:
                results.append({
                    "platform": platform,
                    "success": True,
                    "content": result.answer,
                    "model": getattr(adapter, 'model', ''),
                    "tokens_input": result.tokens_input or 0,
                    "tokens_output": result.tokens_output or 0,
                })
            else:
                results.append({
                    "platform": platform,
                    "success": False,
                    "error": result.error,
                    "content": "",
                })
        except Exception as e:
            results.append({
                "platform": platform,
                "success": False,
                "error": str(e),
                "content": "",
            })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "question": req.message,
            "sources": sources,
            "results": results,
        }
    }


# ============ 流式输出（SSE） ============

@router.post("/chat/stream", summary="流式对话（SSE）")
def chat_stream(
    req: ChatSendRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """流式对话，SSE格式返回，逐token推送"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 1. 获取或创建会话
    if req.session_id:
        session = db.query(AssetChatSession).filter(
            AssetChatSession.id == req.session_id,
            AssetChatSession.user_id == user_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        session.platform = req.platform
    else:
        session = AssetChatSession(
            user_id=user_id,
            document_id=req.document_id,
            platform=req.platform,
            title=req.message[:30] + "..." if len(req.message) > 30 else req.message,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. 保存用户消息
    user_msg = AssetChatMessage(
        session_id=session.id,
        user_id=user_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    db.commit()

    # 3. RAG检索相关知识
    query_vec = asset_embedder.embed_text(req.message)
    chunk_query = db.query(AssetChunk).filter(
        AssetChunk.user_id == user_id,
        AssetChunk.embedding != "",
    )
    if req.document_id:
        chunk_query = chunk_query.filter(AssetChunk.document_id == req.document_id)

    chunks = chunk_query.all()
    context_parts = []
    sources = []
    if chunks:
        chunk_scores = []
        for chunk in chunks:
            chunk_vec = asset_embedder.json_to_vector(chunk.embedding)
            if not chunk_vec:
                continue
            score = asset_embedder.cosine_similarity(query_vec, chunk_vec)
            chunk_scores.append((chunk, score))
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        seen_docs = set()
        for chunk, score in chunk_scores[:req.top_k * 2]:
            doc = db.query(AssetDocument).filter(AssetDocument.id == chunk.document_id).first()
            if not doc:
                continue
            context_parts.append(f"【{doc.title}】\n{chunk.content}")
            if doc.id not in seen_docs:
                seen_docs.add(doc.id)
                sources.append({"id": doc.id, "title": doc.title, "score": float(score)})
            if len(context_parts) >= req.top_k:
                break

    context = "\n\n".join(context_parts) if context_parts else "（知识库中未找到相关内容）"

    # 4. 构建system_prompt
    system_prompt = f"""你是一位专业的医学知识助手。请基于用户的个人知识库内容回答问题。

要求：
1. 主要使用知识库中提供的信息回答，不要编造
2. 如果知识库中没有相关信息，可以基于你的专业知识补充，但要明确标注
3. 回答要专业、准确、简洁，符合医疗行业规范

知识库内容：
{context}
"""

    # 5. 获取适配器
    adapter = adapter_factory.get_adapter(req.platform)
    if not adapter:
        enabled = adapter_factory.get_enabled_platforms()
        if not enabled:
            raise HTTPException(status_code=400, detail="未配置可用的AI模型")
        adapter = adapter_factory.get_adapter(enabled[0])
        req.platform = enabled[0]

    # 6. SSE生成器
    def generate():
        full_answer = ""
        tokens_input = 0
        tokens_output = 0

        try:
            # 先发送元数据（会话ID + 引用来源）
            import json
            meta = {
                "type": "meta",
                "session_id": session.id,
                "platform": req.platform,
                "sources": sources,
            }
            yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

            # 流式调用
            for text_chunk, is_finished, usage in adapter.query_stream(
                req.message,
                system_prompt=system_prompt,
            ):
                if usage:
                    tokens_input = usage.get("tokens_input", 0)
                    tokens_output = usage.get("tokens_output", 0)

                if is_finished:
                    # 流式结束，保存消息到数据库
                    assistant_msg = AssetChatMessage(
                        session_id=session.id,
                        user_id=user_id,
                        role="assistant",
                        content=full_answer,
                        platform=req.platform,
                        model=getattr(adapter, 'model', ''),
                        tokens_input=tokens_input,
                        tokens_output=tokens_output,
                        sources=json.dumps(sources, ensure_ascii=False),
                    )
                    db.add(assistant_msg)
                    db.commit()

                    # 更新会话时间
                    import datetime
                    session.updated_at = datetime.datetime.now()
                    db.commit()

                    # 发送完成事件
                    done_event = {"type": "done"}
                    yield f"data: {json.dumps(done_event)}\n\n"
                else:
                    full_answer += text_chunk
                    # 发送文本片段
                    chunk_event = {"type": "chunk", "content": text_chunk}
                    yield f"data: {json.dumps(chunk_event, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
