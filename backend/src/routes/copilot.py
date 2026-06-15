"""
Copilot 交互 API - 提供聊天接口供前端调用。
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from src.routes.auth import get_current_user, get_admin_user

logger = logging.getLogger("copilot.api")
router = APIRouter(dependencies=[Depends(get_current_user)])

# status_router 始终注册，不需要认证（前端需要检测 Copilot 状态）
status_router = APIRouter()

_copilot_instance = None


def set_copilot(copilot):
    global _copilot_instance
    _copilot_instance = copilot


def get_copilot():
    return _copilot_instance


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    copilot_enabled: bool = True


class ScanResponse(BaseModel):
    report: str


@router.post("/chat", response_model=ChatResponse)
async def copilot_chat(data: ChatRequest, user: dict = Depends(get_current_user)):
    copilot = get_copilot()
    if not copilot:
        raise HTTPException(503, "Copilot is not enabled")

    response = await copilot.aask(data.message)
    return ChatResponse(response=response, copilot_enabled=True)


@router.post("/scan", response_model=ScanResponse)
async def copilot_scan(user: dict = Depends(get_admin_user)):
    copilot = get_copilot()
    if not copilot:
        raise HTTPException(503, "Copilot is not enabled")

    report = await copilot.ascan()
    return ScanResponse(report=report)


@status_router.get("/status")
async def copilot_status():
    copilot = get_copilot()
    return {
        "enabled": copilot is not None,
        "model": copilot.model if copilot else None,
    }
