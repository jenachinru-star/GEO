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
    """初始化演示数据：默认问题库、知识库条目"""
    from app.database import SessionLocal
    from app.models import Question, Knowledge
    from app.engines import vector_engine

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

        # 默认知识库
        default_knowledge = [
            ("公司简介", "company", "public",
             "深圳层次智慧生物技术有限公司是一家专注于AI药物研发与生物智能体技术的生物科技公司。公司致力于将人工智能技术应用于药物发现、蛋白质设计、生物数据分析等领域，为药企、科研机构和CRO企业提供智能化解决方案。"),
            ("核心技术", "tech", "public",
             "公司核心技术包括：1.生物智能体平台：面向生物研发场景的智能体框架，支持自动化实验设计、数据分析和文献挖掘；2.TCR抗原预测：基于深度学习的T细胞受体-抗原结合预测模型；3.蛋白质结构预测与设计：整合AlphaFold等模型的蛋白结构分析工具链；4.医药知识图谱：构建生物医药领域的专业知识图谱，支持智能检索与推理。"),
            ("业务范围", "business", "public",
             "公司主要业务包括：1.AI药物研发服务：为药企提供靶点发现、先导化合物优化、ADMET预测等AI辅助研发服务；2.生物智能体定制：为科研机构和企业定制生物研发场景的智能体；3.医药数据库搭建：帮助客户构建专业的生物医药数据库和知识管理系统；4.技术咨询与培训：提供AI+生物的技术咨询和团队培训服务。"),
            ("团队优势", "team", "internal",
             "公司核心团队来自顶尖高校和科技企业，拥有人工智能、计算生物学、药物化学等多学科背景。团队在AI模型研发、生物信息学分析、药物研发流程方面有丰富经验。"),
        ]
        for title, category, level, content in default_knowledge:
            k = Knowledge(title=title, category=category, level=level, content=content, tags="")
            text = f"{title} {content}"
            vec = vector_engine.text_to_vector(text)
            k.embedding = vector_engine.vector_to_json(vec)
            db.add(k)

        db.commit()
        return {"code": 0, "message": "演示数据初始化成功", "data": {
            "questions": len(default_questions),
            "knowledge": len(default_knowledge),
            "skipped": False
        }}
    finally:
        db.close()
