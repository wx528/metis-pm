"""API 防抖工具：短时间内相同内容的写请求自动去重"""
import hashlib
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException

# 防抖窗口：{fingerprint: expire_timestamp}
_debounce_store: dict[str, float] = {}

# 默认防抖窗口（秒）
DEFAULT_DEBOUNCE_WINDOW = 10


def _fingerprint(path: str, body: bytes, user_sub: str) -> str:
    """生成请求指纹：路径 + 请求体 + 用户"""
    raw = f"{path}:{user_sub}:{body!r}"
    return hashlib.md5(raw.encode()).hexdigest()


def check_debounce(path: str, body: bytes, user_sub: str,
                   window: float = DEFAULT_DEBOUNCE_WINDOW) -> Optional[str]:
    """检查防抖，返回 None 表示通过，返回字符串表示被防抖拦截

    Args:
        path: API 路径
        body: 请求体原始字节
        user_sub: 用户标识
        window: 防抖窗口（秒）

    Returns:
        None = 通过，str = 拦截原因
    """
    fp = _fingerprint(path, body, user_sub)
    now = time.monotonic()

    # 清理过期条目（懒清理，每次检查时顺便清理）
    expired = [k for k, v in _debounce_store.items() if v < now]
    for k in expired:
        _debounce_store.pop(k, None)

    if fp in _debounce_store:
        remaining = int(_debounce_store[fp] - now)
        return f"请求过于频繁，相同内容请在 {remaining} 秒后再试"

    _debounce_store[fp] = now + window
    return None


def debounce_check_or_raise(path: str, body: bytes, user_sub: str,
                            window: float = DEFAULT_DEBOUNCE_WINDOW):
    """防抖检查，被拦截时抛出 HTTPException"""
    msg = check_debounce(path, body, user_sub, window)
    if msg:
        raise HTTPException(status_code=429, detail=msg)
