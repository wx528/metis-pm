from typing import List, Optional
import socket
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone

from src.core.dependencies import get_db
from src.models.server import Server
from src.models.activity_log import ActivityLog
from src.schemas.server import ServerCreate, ServerUpdate, ServerRead, ServerCredentials
from src.routes.auth import get_current_user, get_admin_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[ServerRead])
async def list_servers(
    db: AsyncSession = Depends(get_db),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    server_type: Optional[str] = Query(None),
):
    """服务器列表（支持筛选）"""
    query = select(Server).order_by(desc(Server.created_at))
    if project_id:
        query = query.where(Server.project_id == project_id)
    if status:
        query = query.where(Server.status == status)
    if environment:
        query = query.where(Server.environment == environment)
    if server_type:
        query = query.where(Server.server_type == server_type)
    result = await db.execute(query)
    return [ServerRead.from_orm_with_flags(s) for s in result.scalars().all()]


@router.post("", response_model=ServerRead, status_code=201)
async def create_server(data: ServerCreate, db: AsyncSession = Depends(get_db)):
    """创建服务器"""
    server = Server(**data.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return ServerRead.from_orm_with_flags(server)


@router.get("/{server_id}", response_model=ServerRead)
async def get_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """服务器详情"""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerRead.from_orm_with_flags(server)


@router.put("/{server_id}", response_model=ServerRead)
async def update_server(server_id: int, data: ServerUpdate, db: AsyncSession = Depends(get_db)):
    """更新服务器"""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(server, key, value)

    await db.commit()
    await db.refresh(server)
    return ServerRead.from_orm_with_flags(server)


@router.delete("/{server_id}", status_code=204)
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """删除服务器"""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.delete(server)
    await db.commit()
    return None


@router.get("/{server_id}/credentials", response_model=ServerCredentials)
async def get_server_credentials(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_admin_user),
):
    """获取服务器凭据（仅 admin 角色，带审计日志）"""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    # 审计日志：记录谁在何时获取了哪台服务器的凭据
    log = ActivityLog(
        entity_type="server",
        entity_id=server_id,
        action="credentials_viewed",
        actor=user.get("sub", "unknown"),
        new_value={"info": f"Credentials viewed by {user.get('sub', 'unknown')}"},
    )
    db.add(log)
    await db.commit()
    return server


@router.post("/{server_id}/check", response_model=ServerRead)
async def check_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """手动触发服务器状态检查（TCP 连通性测试）"""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.last_checked_at = datetime.now(timezone.utc)

    # TCP 连通性检查
    if server.ip_address and server.port:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((server.ip_address, server.port))
            sock.close()
            # 可连通，如果之前是 offline 则恢复为 active
            from src.models.server import ServerStatus
            if server.status == ServerStatus.OFFLINE:
                server.status = ServerStatus.ACTIVE
        except (socket.timeout, socket.error, OSError):
            # 不可连通，标记为 offline
            from src.models.server import ServerStatus
            server.status = ServerStatus.OFFLINE
    # 无 IP/端口信息时，仅更新 last_checked_at

    await db.commit()
    await db.refresh(server)
    return ServerRead.from_orm_with_flags(server)
