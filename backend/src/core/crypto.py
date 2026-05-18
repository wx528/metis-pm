"""Fernet 对称加密工具 — 用于加密服务器凭据（password / ssh_key）"""
import os
from cryptography.fernet import Fernet

from src.settings import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY not set. Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    _fernet = Fernet(key.encode())
    return _fernet


def encrypt_value(plain: str | None) -> str | None:
    """加密明文字符串，返回 base64 编码的密文。None / 空串原样返回。"""
    if not plain:
        return plain
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_value(cipher: str | None) -> str | None:
    """解密密文字符串，返回明文。None / 空串原样返回。"""
    if not cipher:
        return cipher
    return _get_fernet().decrypt(cipher.encode()).decode()
