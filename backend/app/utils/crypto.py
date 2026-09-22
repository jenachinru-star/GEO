import os
from cryptography.fernet import Fernet
from app.config import settings

_fernet = None

def _get_fernet():
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPT_KEY
        if not key:
            # 开发环境自动生成（生产环境必须设置ENCRYPT_KEY）
            key = Fernet.generate_key().decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet

def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""  # 解密失败返回空，不抛异常
