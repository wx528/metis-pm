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


class MeResponse(BaseModel):
    role: str = "admin"


def create_token() -> str:
    """创建 JWT token（有效期 24 小时）"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "admin",
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    """验证 JWT token"""
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


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    """登录"""
    if data.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token()
    return {"token": token}


@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)):
    """当前用户信息"""
    return {"role": "admin"}
