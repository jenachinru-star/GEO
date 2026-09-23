"""AI平台配置管理 API - 支持数据库动态配置，热更新生效

功能：
- 获取平台列表（含配置状态）
- 创建/更新/删除平台配置
- 启用/停用平台
- 测试平台连接（调用一次 API 验证配置是否有效）
- 重新加载适配器（配置变更后热更新）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.database import get_db
from app.deps import get_current_admin_id
from app.models.platform import Platform
from app.adapters import adapter_factory
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/platforms", tags=["AI平台配置管理"])


# ============ 请求体模型 ============

class PlatformCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="平台标识，如 glm/minimax/doubao")
    name: str = Field(..., min_length=2, max_length=100, description="平台显示名称")
    base_url: str = Field(..., min_length=10, max_length=500, description="API 基础地址")
    api_key: str = Field(..., min_length=10, max_length=500, description="API Key")
    model: str = Field(..., min_length=2, max_length=100, description="默认模型")
    status: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级，数字越大越优先")
    timeout: int = Field(30, ge=5, le=300, description="超时时间（秒）")
    max_tokens: int = Field(2000, ge=100, le=32000, description="最大输出 token")
    temperature: float = Field(0.3, ge=0, le=2, description="温度参数")
    description: str = Field("", max_length=500, description="平台描述")
    platform_type: str = Field("openai_compatible", description="平台类型：openai_compatible/image")
    extra_config: dict = Field(default_factory=dict, description="额外配置")


class PlatformUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = Field(None, max_length=100)
    status: Optional[bool] = None
    priority: Optional[int] = None
    timeout: Optional[int] = Field(None, ge=5, le=300)
    max_tokens: Optional[int] = Field(None, ge=100, le=32000)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    description: Optional[str] = Field(None, max_length=500)
    platform_type: Optional[str] = None
    extra_config: Optional[dict] = None


class PlatformTestRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    platform_code: Optional[str] = None  # 测试已存在的平台时传 code


# ============ 平台列表 ============

@router.get("", summary="获取平台配置列表")
def list_platforms(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """获取所有平台配置（管理员可见完整配置，api_key 脱敏）"""
    platforms = db.query(Platform).order_by(Platform.priority.desc(), Platform.id.asc()).all()

    # 合并 .env 中的默认配置（数据库没有的平台从 .env 读取）
    env_platforms = _get_env_platforms()
    db_codes = {p.code for p in platforms}

    result = [p.to_dict() for p in platforms]

    # 补充 .env 中已配置但数据库没有的平台
    for env_p in env_platforms:
        if env_p["code"] not in db_codes:
            env_p["source"] = "env"  # 标记来自 .env
            result.append(env_p)

    return {"code": 0, "message": "success", "data": result}


def _get_env_platforms() -> List[dict]:
    """从 .env 读取默认平台配置（作为兜底）"""
    env_platforms = []

    # DeepSeek
    if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_BASE_URL:
        env_platforms.append({
            "code": "deepseek", "name": "DeepSeek",
            "base_url": settings.DEEPSEEK_BASE_URL, "model": settings.DEEPSEEK_MODEL,
            "status": True, "priority": 0, "timeout": 30,
            "max_tokens": settings.MONITOR_MAX_TOKENS, "temperature": settings.MONITOR_TEMPERATURE,
            "description": "DeepSeek（来自 .env 配置）", "platform_type": "openai_compatible",
            "configured": True, "api_key_masked": settings.DEEPSEEK_API_KEY[:4] + "****" + settings.DEEPSEEK_API_KEY[-4:],
        })

    # GLM
    if settings.GLM_API_KEY and settings.GLM_BASE_URL:
        env_platforms.append({
            "code": "glm", "name": "GLM",
            "base_url": settings.GLM_BASE_URL, "model": settings.GLM_MODEL,
            "status": True, "priority": 0, "timeout": 30,
            "max_tokens": settings.MONITOR_MAX_TOKENS, "temperature": settings.MONITOR_TEMPERATURE,
            "description": "智谱清言 GLM（来自 .env 配置）", "platform_type": "openai_compatible",
            "configured": True, "api_key_masked": settings.GLM_API_KEY[:4] + "****" + settings.GLM_API_KEY[-4:],
        })

    # MiniMax
    if settings.MINIMAX_API_KEY and settings.MINIMAX_BASE_URL:
        env_platforms.append({
            "code": "minimax", "name": "MiniMax",
            "base_url": settings.MINIMAX_BASE_URL, "model": settings.MINIMAX_MODEL,
            "status": True, "priority": 0, "timeout": 30,
            "max_tokens": settings.MONITOR_MAX_TOKENS, "temperature": settings.MONITOR_TEMPERATURE,
            "description": "MiniMax（来自 .env 配置）", "platform_type": "openai_compatible",
            "configured": True, "api_key_masked": settings.MINIMAX_API_KEY[:4] + "****" + settings.MINIMAX_API_KEY[-4:],
        })

    # 豆包（预留）
    if settings.DOUBAO_API_KEY and settings.DOUBAO_BASE_URL:
        env_platforms.append({
            "code": "doubao", "name": "豆包",
            "base_url": settings.DOUBAO_BASE_URL, "model": settings.DOUBAO_MODEL or "",
            "status": True, "priority": 0, "timeout": 30,
            "max_tokens": settings.MONITOR_MAX_TOKENS, "temperature": settings.MONITOR_TEMPERATURE,
            "description": "字节豆包（来自 .env 配置）", "platform_type": "openai_compatible",
            "configured": True, "api_key_masked": settings.DOUBAO_API_KEY[:4] + "****" + settings.DOUBAO_API_KEY[-4:],
        })

    # 通义千问（预留）
    if settings.QWEN_API_KEY and settings.QWEN_BASE_URL:
        env_platforms.append({
            "code": "qwen", "name": "通义千问",
            "base_url": settings.QWEN_BASE_URL, "model": settings.QWEN_MODEL or "",
            "status": True, "priority": 0, "timeout": 30,
            "max_tokens": settings.MONITOR_MAX_TOKENS, "temperature": settings.MONITOR_TEMPERATURE,
            "description": "阿里通义千问（来自 .env 配置）", "platform_type": "openai_compatible",
            "configured": True, "api_key_masked": settings.QWEN_API_KEY[:4] + "****" + settings.QWEN_API_KEY[-4:],
        })

    return env_platforms


# ============ 获取单个平台 ============

@router.get("/{platform_code}", summary="获取单个平台配置详情")
def get_platform(
    platform_code: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """获取单个平台配置详情（含 api_key，管理员可见）"""
    platform = db.query(Platform).filter(Platform.code == platform_code).first()
    if not platform:
        raise HTTPException(status_code=404, detail="平台不存在")
    return {"code": 0, "message": "success", "data": platform.to_dict(include_api_key=True)}


# ============ 创建平台 ============

@router.post("", summary="创建平台配置")
def create_platform(
    req: PlatformCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """创建新的平台配置"""
    # 检查 code 是否已存在
    existing = db.query(Platform).filter(Platform.code == req.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"平台标识 {req.code} 已存在")

    platform = Platform(
        code=req.code,
        name=req.name,
        base_url=req.base_url,
        api_key=req.api_key,
        model=req.model,
        status=req.status,
        priority=req.priority,
        timeout=req.timeout,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        description=req.description,
        platform_type=req.platform_type,
        extra_config=req.extra_config,
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)

    # 热更新适配器（从Platform表重新加载）
    adapter_factory.reload_from_db(db)
    logger.info(f"创建平台配置: {req.code} ({req.name})，已热更新适配器")

    return {"code": 0, "message": "创建成功", "data": platform.to_dict()}


# ============ 更新平台 ============

@router.put("/{platform_code}", summary="更新平台配置")
def update_platform(
    platform_code: str,
    req: PlatformUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """更新平台配置"""
    platform = db.query(Platform).filter(Platform.code == platform_code).first()
    if not platform:
        raise HTTPException(status_code=404, detail="平台不存在")

    update_data = req.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(platform, key, value)

    db.commit()
    db.refresh(platform)

    # 热更新适配器（从Platform表重新加载）
    adapter_factory.reload_from_db(db)
    logger.info(f"更新平台配置: {platform_code}，已热更新适配器")

    return {"code": 0, "message": "更新成功", "data": platform.to_dict()}


# ============ 删除平台 ============

@router.delete("/{platform_code}", summary="删除平台配置")
def delete_platform(
    platform_code: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """删除平台配置"""
    platform = db.query(Platform).filter(Platform.code == platform_code).first()
    if not platform:
        raise HTTPException(status_code=404, detail="平台不存在")

    db.delete(platform)
    db.commit()

    # 热更新适配器（从Platform表重新加载）
    adapter_factory.reload_from_db(db)
    logger.info(f"删除平台配置: {platform_code}，已热更新适配器")

    return {"code": 0, "message": "删除成功"}


# ============ 启用/停用平台 ============

@router.post("/{platform_code}/toggle", summary="启用/停用平台")
def toggle_platform(
    platform_code: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """切换平台启用状态"""
    platform = db.query(Platform).filter(Platform.code == platform_code).first()
    if not platform:
        raise HTTPException(status_code=404, detail="平台不存在")

    platform.status = not platform.status
    db.commit()
    db.refresh(platform)

    # 热更新适配器（从Platform表重新加载）
    adapter_factory.reload_from_db(db)
    logger.info(f"切换平台状态: {platform_code} -> {'启用' if platform.status else '停用'}，已热更新")

    return {"code": 0, "message": "操作成功", "data": {"status": platform.status}}


# ============ 测试平台连接 ============

@router.post("/test", summary="测试平台连接")
def test_platform(
    req: PlatformTestRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """测试平台配置是否有效（调用一次简单的 API 请求）

    可以测试已存在的平台（传 platform_code），也可以测试新配置（传 base_url/api_key/model）
    """
    from app.adapters.openai_compatible import OpenAICompatibleAdapter

    # 如果传了 platform_code，从数据库读取配置
    if req.platform_code:
        platform = db.query(Platform).filter(Platform.code == req.platform_code).first()
        if not platform:
            raise HTTPException(status_code=404, detail="平台不存在")
        base_url = platform.base_url
        api_key = platform.api_key
        model = platform.model
        platform_code = platform.code
    else:
        # 用传入的配置测试
        if not all([req.base_url, req.api_key, req.model]):
            raise HTTPException(status_code=400, detail="测试新配置时必须传 base_url、api_key、model")
        base_url = req.base_url
        api_key = req.api_key
        model = req.model
        platform_code = "test"

    try:
        # 创建临时适配器测试
        adapter = OpenAICompatibleAdapter(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.1,
            max_tokens=50,
        )
        adapter.platform_code = platform_code
        result = adapter.query("你好，请回复'连接成功'")

        if result.success:
            return {
                "code": 0,
                "message": "连接成功",
                "data": {
                    "success": True,
                    "answer": result.answer[:200],
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "total_tokens": result.total_tokens,
                    "latency_ms": 0,  # 临时适配器不记录延迟
                }
            }
        else:
            return {
                "code": 0,
                "message": "连接失败",
                "data": {
                    "success": False,
                    "error": result.error[:500] if result.error else "未知错误",
                }
            }
    except Exception as e:
        logger.error(f"测试平台连接异常: {e}")
        return {
            "code": 0,
            "message": "连接异常",
            "data": {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)[:500]}",
            }
        }


# ============ 重新加载适配器 ============

@router.post("/reload", summary="重新加载适配器（热更新）")
def reload_adapters(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """手动触发适配器重新加载（一般不需要，配置变更时会自动 reload）"""
    adapter_factory.reload_from_db(db)
    enabled = adapter_factory.get_enabled_platforms()
    logger.info(f"手动重新加载适配器，当前启用平台: {enabled}")
    return {"code": 0, "message": "重载成功", "data": {"enabled_platforms": enabled}}
