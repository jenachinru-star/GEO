"""用量治理 — 配额检查 + 平台开关检查

在 adapter.query() 调用前执行：
1. 用户是否启用了该平台
2. 用户当月费用是否超限
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.usage import LlmUsageLog
from app.models.user_platform_pref import UserPlatformPref
from app.models.user_quota import UserQuota
from app.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_QUOTA = 19.9  # 新用户默认月配额（元）


class QuotaError(Exception):
    """配额/开关检查不通过"""
    def __init__(self, message: str, code: str = "quota_exceeded"):
        self.message = message
        self.code = code
        super().__init__(message)


def ensure_user_quota(db: Session, user_id: int) -> UserQuota:
    """确保用户有配额记录，没有则创建默认值"""
    q = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
    if not q:
        q = UserQuota(user_id=user_id, monthly_cost_limit=DEFAULT_QUOTA)
        db.add(q)
        db.commit()
        db.refresh(q)
        logger.info(f"为用户 {user_id} 创建默认配额: {DEFAULT_QUOTA}元/月")
    return q


def check_platform_enabled(db: Session, user_id: int, platform_code: str) -> None:
    """检查用户是否启用了该平台。未设置记录默认启用。"""
    pref = db.query(UserPlatformPref).filter(
        UserPlatformPref.user_id == user_id,
        UserPlatformPref.platform_code == platform_code,
    ).first()
    if pref and not pref.enabled:
        raise QuotaError(
            f"该AI模型已被您停用，请在「用量管理」中开启后再使用",
            code="platform_disabled"
        )


def get_monthly_cost(db: Session, user_id: int) -> float:
    """获取用户当月已消耗的费用（元）"""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = db.query(func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0.0)).filter(
        LlmUsageLog.user_id == user_id,
        LlmUsageLog.created_at >= month_start,
    ).scalar()
    return round(float(total or 0), 4)


def check_quota(db: Session, user_id: int) -> None:
    """检查用户当月配额是否超限。管理员(-1)不检查。"""
    # 查用户角色
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise QuotaError("用户不存在", code="user_not_found")
    if user.role == "admin":
        return  # 管理员不限

    # 确保配额记录存在
    quota = ensure_user_quota(db, user_id)

    # -1 = 无限
    if quota.monthly_cost_limit and quota.monthly_cost_limit < 0:
        return

    used = get_monthly_cost(db, user_id)
    limit = quota.monthly_cost_limit

    if used >= limit:
        raise QuotaError(
            f"本月AI用量费用已达 {used:.2f} 元 / {limit:.2f} 元，配额已用尽。如需提升请联系管理员。",
            code="quota_exceeded"
        )


def check_all(db: Session, user_id: int, platform_code: str) -> None:
    """一站式检查：平台开关 + 配额"""
    check_platform_enabled(db, user_id, platform_code)
    check_quota(db, user_id)
