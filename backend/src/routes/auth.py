from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from src.settings import settings

router = APIRouter()
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    sub: str
    role: str


class MeResponse(BaseModel):
    sub: str
    role: str


def create_token(sub: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    return verify_token(credentials)


async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """仅允许 admin 角色访问"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def verify_api_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """验证外部 API Token（独立于用户 JWT 认证）。

    Token 在 settings.API_TOKENS_JSON 中配置，格式：
    {"tk-abc123": {"name": "ci-bot", "role": "external"}, ...}

    返回: {"sub": "ci-bot", "role": "external"}
    """
    from src.settings import settings
    token = credentials.credentials
    token_info = settings.api_token_map.get(token)
    if not token_info:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return {"sub": token_info.get("name", "unknown"), "role": token_info.get("role", "external")}


def require_role(*allowed_roles: str):
    """角色权限校验工厂：仅允许指定角色访问"""
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            roles_str = "/".join(allowed_roles)
            raise HTTPException(status_code=403, detail=f"{roles_str} role required, got '{user.get('role', 'unknown')}'")
        return user
    return _checker


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    identity = settings.resolve_identity(data.password)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid password")
    sub, role = identity
    token = create_token(sub, role)
    return {"token": token, "sub": sub, "role": role}


@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)):
    return {"sub": user.get("sub", "unknown"), "role": user.get("role", "unknown")}
