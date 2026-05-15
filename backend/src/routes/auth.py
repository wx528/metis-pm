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
