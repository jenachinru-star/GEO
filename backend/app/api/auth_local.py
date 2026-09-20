"""本地账号认证 API — 邮箱注册/登录（对外用户）

与 IAM 企业登录并存：
- 本地账号：面向对外医生用户，邮箱注册 + 密码登录
- IAM 登录：面向公司内部员工，企业 SSO

功能：
- 发送邮箱验证码（注册/重置密码）
- 用户注册（邮箱 + 验证码 + 密码）
- 用户登录（邮箱 + 密码）
- 重置密码（邮箱 + 验证码 + 新密码）
- 修改密码（登录后，旧密码 + 新密码）
"""
import time
import secrets
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
import jwt

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.services.email_service import email_service
from app.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/local", tags=["本地账号认证"])

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 验证码配置
CODE_EXPIRE_MINUTES = 5
CODE_RESEND_SECONDS = 60
CODE_LENGTH = 6

# 登录失败锁定配置（内存存储，简单实现）
_login_failures: dict = {}  # {email: {"count": int, "lock_until": float}}
MAX_LOGIN_FAILURES = 5
LOCK_DURATION_SECONDS = 15 * 60  # 15 分钟


# ============ 请求体模型 ============

class SendCodeRequest(BaseModel):
    email: EmailStr
    type: str = Field("register", description="验证码类型：register / reset")


class RegisterRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=6, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=64)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=64)


# ============ 工具函数 ============

def _generate_jwt(user: User) -> str:
    """生成 JWT token（复用 IAM 相同的格式和密钥）"""
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": time.time() + settings.JWT_EXPIRE_HOURS * 3600,
        "iat": time.time(),
        "login_type": "local",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def _hash_password(password: str) -> str:
    """密码加密"""
    return pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def _check_login_lock(email: str):
    """检查登录是否被锁定"""
    record = _login_failures.get(email)
    if not record:
        return
    if record["lock_until"] and time.time() < record["lock_until"]:
        remain = int(record["lock_until"] - time.time())
        raise HTTPException(status_code=429, detail=f"登录失败次数过多，请 {remain} 秒后再试")
    # 锁定已过期，清除记录
    if record["lock_until"] and time.time() >= record["lock_until"]:
        _login_failures.pop(email, None)


def _record_login_failure(email: str):
    """记录登录失败"""
    record = _login_failures.get(email, {"count": 0, "lock_until": None})
    record["count"] += 1
    if record["count"] >= MAX_LOGIN_FAILURES:
        record["lock_until"] = time.time() + LOCK_DURATION_SECONDS
        record["count"] = 0
    _login_failures[email] = record


def _clear_login_failures(email: str):
    """清除登录失败记录（登录成功后调用）"""
    _login_failures.pop(email, None)


def _generate_code() -> str:
    """生成 6 位数字验证码"""
    return "".join([str(secrets.randbelow(10)) for _ in range(CODE_LENGTH)])


def _verify_code(db: Session, email: str, code: str, code_type: str) -> bool:
    """验证验证码是否有效（验证后标记为已使用）"""
    record = db.query(VerificationCode).filter(
        VerificationCode.email == email,
        VerificationCode.code == code,
        VerificationCode.type == code_type,
        VerificationCode.used == False,
    ).order_by(VerificationCode.id.desc()).first()

    if not record:
        return False
    if datetime.now() > record.expire_at:
        return False

    # 标记为已使用
    record.used = True
    db.commit()
    return True


# ============ 检查邮箱是否已注册 ============

@router.get("/check-email", summary="检查邮箱是否已注册")
def check_email(
    email: str,
    db: Session = Depends(get_db),
):
    """检查邮箱是否已被注册，用于前端实时提示"""
    email = email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "exists": existing is not None,
            "email": email,
        }
    }


# ============ 发送验证码 ============

@router.post("/send-code", summary="发送邮箱验证码")
def send_code(
    req: SendCodeRequest,
    db: Session = Depends(get_db),
):
    """发送邮箱验证码（注册或重置密码用）"""
    email = str(req.email).strip().lower()
    code_type = req.type

    # 顺手清理过期验证码（防止表越来越大）
    try:
        db.query(VerificationCode).filter(
            VerificationCode.expire_at < datetime.now()
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()

    if code_type not in ("register", "reset"):
        raise HTTPException(status_code=400, detail="验证码类型错误")

    # 注册时检查邮箱是否已被注册
    if code_type == "register":
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")

    # 重置密码时检查邮箱是否存在
    if code_type == "reset":
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            raise HTTPException(status_code=400, detail="该邮箱未注册")

    # 检查发送频率（60 秒内不能重复发送）
    recent = db.query(VerificationCode).filter(
        VerificationCode.email == email,
        VerificationCode.type == code_type,
    ).order_by(VerificationCode.id.desc()).first()

    if recent and (datetime.now() - recent.created_at).total_seconds() < CODE_RESEND_SECONDS:
        remain = CODE_RESEND_SECONDS - int((datetime.now() - recent.created_at).total_seconds())
        raise HTTPException(status_code=429, detail=f"发送太频繁，请 {remain} 秒后再试")

    # 生成验证码
    code = _generate_code()
    expire_at = datetime.now() + timedelta(minutes=CODE_EXPIRE_MINUTES)

    # 先发送邮件，成功后再保存验证码记录（避免邮件失败后留下记录导致429）
    success = email_service.send_verification_code(email, code, code_type)
    if not success:
        logger.warning(f"验证码邮件发送失败: email={email}")
        raise HTTPException(status_code=500, detail="验证码邮件发送失败，请稍后重试")

    # 邮件发送成功，保存验证码
    vc = VerificationCode(
        email=email,
        code=code,
        type=code_type,
        expire_at=expire_at,
        used=False,
    )
    db.add(vc)
    db.commit()

    return {"code": 0, "message": "success", "data": {"email": email, "expire_minutes": CODE_EXPIRE_MINUTES}}


# ============ 用户注册 ============

@router.post("/register", summary="用户注册（邮箱 + 验证码 + 密码）")
def register(
    req: RegisterRequest,
    db: Session = Depends(get_db),
):
    """用户注册"""
    email = str(req.email).strip().lower()
    code = req.code.strip()
    password = req.password

    # 检查邮箱是否已被注册
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    # 验证验证码
    if not _verify_code(db, email, code, "register"):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 创建用户（username 用邮箱前缀，role 默认 doctor）
    username = email.split("@")[0]
    # 确保 username 唯一
    base_username = username
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{suffix}"
        suffix += 1

    user = User(
        username=username,
        email=email,
        password_hash=_hash_password(password),
        role="doctor",
        status=True,
        login_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 注册成功后自动登录，返回 JWT
    token = _generate_jwt(user)

    logger.info(f"用户注册成功: email={email}, user_id={user.id}")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "login_type": "local",
            }
        }
    }


# ============ 用户登录 ============

@router.post("/login", summary="用户登录（邮箱 + 密码）")
def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
):
    """用户登录"""
    email = str(req.email).strip().lower()
    password = req.password

    # 检查登录锁定
    _check_login_lock(email)

    # 查找用户
    user = db.query(User).filter(User.email == email).first()
    if not user:
        _record_login_failure(email)
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not user.status:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 验证密码（IAM 用户 password_hash 为空，不能用本地登录）
    if not user.password_hash:
        _record_login_failure(email)
        raise HTTPException(status_code=401, detail="该账号为企业账号，请使用企业登录")

    if not _verify_password(password, user.password_hash):
        _record_login_failure(email)
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    # 登录成功，更新登录信息
    user.last_login_at = datetime.now()
    user.login_count = (user.login_count or 0) + 1
    db.commit()

    # 清除登录失败记录
    _clear_login_failures(email)

    # 生成 JWT
    token = _generate_jwt(user)

    logger.info(f"用户登录成功: email={email}, user_id={user.id}")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "login_type": "local",
            }
        }
    }


# ============ 重置密码 ============

@router.post("/reset-password", summary="重置密码（邮箱 + 验证码 + 新密码）")
def reset_password(
    req: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """重置密码（忘记密码用）"""
    email = str(req.email).strip().lower()
    code = req.code.strip()
    new_password = req.new_password

    # 查找用户
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="该邮箱未注册")

    # 验证验证码
    if not _verify_code(db, email, code, "reset"):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 更新密码
    user.password_hash = _hash_password(new_password)
    db.commit()

    logger.info(f"用户重置密码成功: email={email}, user_id={user.id}")

    return {"code": 0, "message": "success", "data": {"email": email}}


# ============ 修改密码（登录后） ============

@router.post("/change-password", summary="修改密码（登录后）")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """修改密码（登录后，需要验证旧密码）"""
    old_password = req.old_password
    new_password = req.new_password

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # IAM 用户无本地密码，不能修改
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="企业账号请在企业系统修改密码")

    # 验证旧密码
    if not _verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    # 更新密码
    user.password_hash = _hash_password(new_password)
    db.commit()

    logger.info(f"用户修改密码成功: user_id={user_id}")

    return {"code": 0, "message": "success"}
