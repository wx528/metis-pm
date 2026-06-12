"""轻量级内存限流中间件

按 IP + 路径限流，无需外部依赖。
适用于单实例部署场景，多实例部署需替换为 Redis 后端。
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按 IP 限流，可配置每秒/每分钟请求数"""

    def __init__(
        self,
        app,
        per_second: int = 20,
        per_minute: int = 200,
        burst: int = 30,
    ):
        super().__init__(app)
        self.per_second = per_second
        self.per_minute = per_minute
        self.burst = burst
        # {ip: {"second_tokens": float, "minute_tokens": float, "last_second": float, "last_minute": float}}
        self._buckets: dict[str, dict] = {}

    def _get_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate(self, ip: str) -> bool:
        """Token bucket 限流检查，返回 True 表示允许"""
        now = time.monotonic()
        bucket = self._buckets.get(ip)
        if not bucket:
            bucket = {
                "second_tokens": float(self.burst),
                "minute_tokens": float(self.per_minute),
                "last_second": now,
                "last_minute": now,
            }
            self._buckets[ip] = bucket

        # 补充秒级令牌
        elapsed_s = now - bucket["last_second"]
        bucket["second_tokens"] = min(
            self.burst, bucket["second_tokens"] + elapsed_s * self.per_second
        )
        bucket["last_second"] = now

        # 补充分钟级令牌
        elapsed_m = now - bucket["last_minute"]
        bucket["minute_tokens"] = min(
            self.per_minute, bucket["minute_tokens"] + elapsed_m * (self.per_minute / 60)
        )
        bucket["last_minute"] = now

        # 消耗令牌
        if bucket["second_tokens"] < 1 or bucket["minute_tokens"] < 1:
            return False

        bucket["second_tokens"] -= 1
        bucket["minute_tokens"] -= 1
        return True

    async def dispatch(self, request: Request, call_next):
        # 不限流健康检查和 metrics
        path = request.url.path
        if path in ("/health", "/metrics") or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        ip = self._get_ip(request)
        if not self._check_rate(ip):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down.",
            )

        return await call_next(request)
