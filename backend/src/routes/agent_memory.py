from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field

from src.core.dependencies import get_db
from src.models.agent_memory import AgentMemory
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(require_role("admin", "agent"))])


class AgentMemoryCreate(BaseModel):
    key: str = Field(..., max_length=200)
    value: str = Field(..., max_length=5000)


class AgentMemoryRead(BaseModel):
    id: int
    agent_id: str
    key: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[AgentMemoryRead])
async def list_agent_memories(
    key_prefix: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出当前 Agent 的记忆"""
    query = select(AgentMemory).where(AgentMemory.agent_id == user["sub"])
    if key_prefix:
        query = query.where(AgentMemory.key.startswith(key_prefix))
    query = query.order_by(desc(AgentMemory.updated_at)).limit(limit)
    result = await db.execute(query)
    memories = result.scalars().all()
    return memories


@router.post("", response_model=AgentMemoryRead, status_code=201)
async def set_agent_memory(
    data: AgentMemoryCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """设置 Agent 记忆（key 相同则更新）"""
    result = await db.execute(
        select(AgentMemory).where(
            AgentMemory.agent_id == user["sub"],
            AgentMemory.key == data.key,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = data.value
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        memory = AgentMemory(agent_id=user["sub"], key=data.key, value=data.value)
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory


@router.delete("/{memory_id}", status_code=204)
async def delete_agent_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除 Agent 记忆"""
    result = await db.execute(select(AgentMemory).where(AgentMemory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if memory.agent_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your memory")
    await db.delete(memory)
    await db.commit()
    return None
