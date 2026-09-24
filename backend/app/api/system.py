from fastapi import APIRouter, Depends
from app.adapters import adapter_factory
from app.config import settings
from app.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/system", tags=["系统"])


@router.get("/info", summary="获取系统信息")
def get_system_info():
    return {
        "code": 0,
        "message": "success",
        "data": {
            "app_name": settings.APP_NAME,
            "version": "1.0.0",
            "enabled_platforms": adapter_factory.get_enabled_platforms()
        }
    }


@router.get("/platforms", summary="获取平台配置状态")
def get_platforms(user_id: int = Depends(get_current_user_id)):
    platforms = []
    platform_configs = [
        ("deepseek", "DeepSeek", settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_MODEL),
        ("glm", "GLM", settings.GLM_API_KEY, settings.GLM_MODEL),
        ("minimax", "MiniMax", settings.MINIMAX_API_KEY, settings.MINIMAX_MODEL),
        ("doubao", "豆包", settings.DOUBAO_API_KEY, settings.DOUBAO_MODEL),
        ("qwen", "通义千问", settings.QWEN_API_KEY, settings.QWEN_MODEL),
    ]
    for code, name, api_key, model in platform_configs:
        platforms.append({
            "code": code,
            "name": name,
            "configured": bool(api_key),
            "model": model,
            "enabled": code in adapter_factory.get_enabled_platforms()
        })
    return {"code": 0, "message": "success", "data": platforms}


@router.post("/init-demo", summary="初始化演示数据")
def init_demo_data(user_id: int = Depends(get_current_user_id)):
    """初始化演示数据：默认问题库"""
    from app.database import SessionLocal
    from app.models import Question

    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(Question).count() > 0:
            return {"code": 0, "message": "已有数据，跳过初始化", "data": {"skipped": True}}

        # 默认问题库
        default_questions = [
            ("深圳有哪些AI药物研发公司", "industry", "行业,AI制药", 10),
            ("国内做生物智能体的公司有哪些", "industry", "行业,生物智能体", 9),
            ("TCR抗原预测服务商推荐", "tech", "技术,TCR", 9),
            ("AI制药公司排名", "industry", "行业,排名", 8),
            ("深圳层次智慧生物技术有限公司怎么样", "brand", "品牌", 10),
            ("层次智慧是做什么的", "brand", "品牌", 10),
            ("计算生物学公司有哪些", "industry", "行业,计算生物", 7),
            ("蛋白质结构预测工具对比", "tech", "技术,蛋白结构", 7),
            ("AI药物研发平台哪家好", "industry", "行业,平台", 8),
            ("生物医药AI技术服务商", "industry", "行业,服务商", 6),
        ]
        for q_text, category, tags, priority in default_questions:
            q = Question(question=q_text, category=category, tags=tags, priority=priority)
            db.add(q)

        db.commit()
        return {"code": 0, "message": "演示数据初始化成功", "data": {
            "questions": len(default_questions),
            "skipped": False
        }}
    finally:
        db.close()
