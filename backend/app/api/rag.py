from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.schemas import RAGQuery, RAGResponse
from app.engines import RAGEngine

router = APIRouter(prefix="/api/v1/rag", tags=["智能问答"])


@router.post("/query", summary="基于知识库的智能问答（支持多轮对话）")
def rag_query(data: RAGQuery, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rag = RAGEngine(db)
    history = [h.model_dump() for h in data.history] if data.history else []
    result = rag.generate_answer(data.query, data.platform, data.level, history)
    return {"code": 0, "message": "success", "data": result}


@router.get("/platforms", summary="获取可用的AI平台")
def get_platforms(user_id: int = Depends(get_current_user_id)):
    from app.adapters import adapter_factory
    platforms = adapter_factory.get_enabled_platforms()
    platform_names = {"deepseek": "DeepSeek", "glm": "GLM", "minimax": "MiniMax", "doubao": "豆包", "qwen": "通义千问"}
    return {"code": 0, "message": "success", "data": [
        {"code": p, "name": platform_names.get(p, p)} for p in platforms
    ]}
