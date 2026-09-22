"""IAM单点登录服务 - 基于Casdoor/OAuth2.0"""
import requests
import secrets
import time
import jwt
import logging
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User

logger = logging.getLogger(__name__)

# 内存存储state（生产环境用Redis）
_state_store: Dict[str, float] = {}
STATE_EXPIRE_SECONDS = 300  # 5分钟过期


class IAMService:
    """IAM单点登录服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_auth_url(self) -> str:
        """生成IAM授权地址"""
        # 生成随机state
        state = secrets.token_hex(16)
        _state_store[state] = time.time()

        params = {
            "client_id": settings.IAM_CLIENT_ID,
            "redirect_uri": settings.IAM_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state
        }
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{settings.IAM_HOST}/login/oauth/authorize?{query}"

    def validate_state(self, state: str) -> bool:
        """验证state有效性（一次性，验证后删除）"""
        if state not in _state_store:
            return False
        create_time = _state_store.pop(state)
        if time.time() - create_time > STATE_EXPIRE_SECONDS:
            return False
        return True

    def exchange_token(self, code: str) -> Optional[Dict]:
        """用授权码换access_token"""
        try:
            resp = requests.post(
                f"{settings.IAM_HOST}/api/login/oauth/access_token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.IAM_CLIENT_ID,
                    "client_secret": settings.IAM_CLIENT_SECRET,
                    "code": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            data = resp.json()
            # 注意：这个接口出错时HTTP仍是200，错误在body里
            if "error" in data:
                logger.error(f"IAM换token失败: {data.get('error_description')}")
                return None
            return data
        except Exception as e:
            logger.error(f"IAM换token异常: {e}")
            return None

    def get_userinfo(self, access_token: str) -> Optional[Dict]:
        """获取用户信息"""
        try:
            resp = requests.get(
                f"{settings.IAM_HOST}/api/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"IAM获取用户信息失败: {resp.status_code}")
                return None
            return resp.json()
        except Exception as e:
            logger.error(f"IAM获取用户信息异常: {e}")
            return None

    def get_or_create_user(self, userinfo: Dict) -> User:
        """根据IAM用户信息获取或创建本地用户（自动建号策略）"""
        iam_user_id = userinfo.get('sub', '')
        username = userinfo.get('preferred_username') or userinfo.get('name') or userinfo.get('sub', 'unknown')
        email = userinfo.get('email', '')

        # 优先按iam_user_id匹配，其次按email匹配（email在IAM系统中也是唯一的）
        user = self.db.query(User).filter(User.iam_user_id == iam_user_id).first()
        if not user and email:
            user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # 确保username唯一
            unique_username = username
            counter = 1
            while self.db.query(User).filter(User.username == unique_username).first():
                unique_username = f"{username}_{counter}"
                counter += 1
            # 自动建号
            user = User(
                username=unique_username,
                email=email or None,
                iam_user_id=iam_user_id,
                password_hash="",  # SSO用户无本地密码
                role="doctor",
                status=True
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"IAM自动创建用户: {unique_username} (iam_user_id={iam_user_id})")

            # 自动创建个人工作空间
            from app.services.workspace_service import ensure_user_workspace
            ensure_user_workspace(self.db, user.id, unique_username)

        return user

    def generate_jwt(self, user: User) -> str:
        """签发JWT token"""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": time.time() + settings.JWT_EXPIRE_HOURS * 3600,
            "iat": time.time()
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def verify_jwt(token: str) -> Optional[Dict]:
        """验证JWT token"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None

    def handle_callback(self, code: str, state: str) -> Tuple[Optional[str], Optional[str]]:
        """处理IAM回调，返回(jwt_token, error_message)"""
        # 1. 验证state
        if not self.validate_state(state):
            return None, "state校验失败，请重新发起登录"

        # 2. 换token
        token_data = self.exchange_token(code)
        if not token_data:
            return None, "获取access_token失败"

        # 3. 获取用户信息
        access_token = token_data.get("access_token")
        userinfo = self.get_userinfo(access_token)
        if not userinfo:
            return None, "获取用户信息失败"

        # 4. 获取或创建用户
        user = self.get_or_create_user(userinfo)

        # 5. 签发JWT
        jwt_token = self.generate_jwt(user)
        return jwt_token, None
