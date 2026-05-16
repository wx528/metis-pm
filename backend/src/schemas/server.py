from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.models.server import ServerType, ServerStatus, ServerEnvironment


class ServerCreate(BaseModel):
    project_id: Optional[int] = None
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    server_type: ServerType = ServerType.OTHER
    status: ServerStatus = ServerStatus.ACTIVE
    environment: ServerEnvironment = ServerEnvironment.DEVELOPMENT
    labels: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    server_type: Optional[ServerType] = None
    status: Optional[ServerStatus] = None
    environment: Optional[ServerEnvironment] = None
    labels: Optional[str] = None
    last_checked_at: Optional[datetime] = None


class ServerRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    has_password: bool = False
    has_ssh_key: bool = False
    server_type: ServerType
    status: ServerStatus
    environment: ServerEnvironment
    labels: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_flags(cls, server: "Server") -> "ServerRead":
        return cls(
            id=server.id,
            project_id=server.project_id,
            name=server.name,
            description=server.description,
            ip_address=server.ip_address,
            port=server.port,
            username=server.username,
            has_password=bool(server.password),
            has_ssh_key=bool(server.ssh_key),
            server_type=server.server_type,
            status=server.status,
            environment=server.environment,
            labels=server.labels,
            last_checked_at=server.last_checked_at,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )


class ServerCredentials(BaseModel):
    """服务器凭据（单独接口返回）"""
    id: int
    name: str
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
