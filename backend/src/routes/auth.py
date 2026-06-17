from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.settings import settings

router = APIRouter()
security = HTTPBearer(auto_error=False)


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == settings.API_KEY:
        return {"sub": "admin", "role": "admin"}
    if credentials:
        token = credentials.credentials
        identity = settings.resolve_identity(token)
        if identity:
            sub, role = identity
            return {"sub": sub, "role": role}
    raise HTTPException(status_code=401, detail="Invalid credentials")


def require_role(*allowed_roles: str):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            roles_str = "/".join(allowed_roles)
            raise HTTPException(status_code=403, detail=f"{roles_str} role required")
        return user
    return _checker


@router.get("/health")
async def health():
    return {"status": "ok"}
