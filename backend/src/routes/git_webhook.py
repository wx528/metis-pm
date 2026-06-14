"""Git Webhook API 路由"""
import secrets
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.git_integration import GitIntegration, IssueCommitLink, PRPlanLink
from src.core.crypto import encrypt_value
from src.core.webhook_handler import process_webhook

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class GitIntegrationCreate(BaseModel):
    project_id: int
    repo_url: str = Field(..., description="仓库 URL，如 https://github.com/owner/repo")
    platform: str = Field(..., description="平台类型: github / gitea / forgejo")
    webhook_secret: str = Field(..., min_length=16, description="Webhook 密钥（至少16位）")
    auto_close_issue: bool = Field(True, description="commit 自动关闭 issue")
    auto_link_pr: bool = Field(True, description="PR 自动关联 plan")
    subscribed_events: List[str] = Field(
        default=["push", "pull_request"],
        description="订阅的事件类型"
    )


class GitIntegrationUpdate(BaseModel):
    repo_url: Optional[str] = None
    webhook_secret: Optional[str] = Field(None, min_length=16)
    auto_close_issue: Optional[bool] = None
    auto_link_pr: Optional[bool] = None
    subscribed_events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class GitIntegrationRead(BaseModel):
    id: int
    project_id: int
    repo_url: str
    platform: str
    webhook_url: Optional[str] = None
    auto_close_issue: bool
    auto_link_pr: bool
    auto_create_issue: bool
    subscribed_events: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CommitLinkRead(BaseModel):
    id: int
    issue_id: int
    commit_hash: str
    commit_short: str
    commit_message: str
    commit_url: Optional[str] = None
    author: str
    action: str
    branch: Optional[str] = None
    committed_at: datetime
    created_at: datetime


class PRPlanLinkRead(BaseModel):
    id: int
    pr_number: int
    pr_title: str
    pr_url: Optional[str] = None
    pr_status: str
    plan_id: int
    author: Optional[str] = None
    merged_at: Optional[datetime] = None
    created_at: datetime


# ─── Webhook 端点（无需认证，通过签名验证）────────────────────────────────────

@router.post("/webhook/git/{platform}")
async def receive_webhook(
    platform: str,
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_hub_signature: Optional[str] = Header(None),
    x_gitea_signature: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_gitea_event: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    接收 Git Webhook 事件
    
    支持平台:
    - GitHub: 使用 X-Hub-Signature-256 头
    - Gitea/Forgejo: 使用 X-Gitea-Signature 头
    
    支持事件:
    - push: 代码推送
    - pull_request: PR 创建/更新/合并
    """
    if platform not in ["github", "gitea", "forgejo"]:
        raise HTTPException(400, f"Unsupported platform: {platform}")
    
    # 获取事件类型
    event_type = x_github_event or x_gitea_event
    if not event_type:
        # 从 payload 推断
        payload = await request.json()
        if "commits" in payload:
            event_type = "push"
        elif "pull_request" in payload:
            event_type = "pull_request"
        else:
            event_type = "unknown"
    
    # 获取签名
    signature = x_hub_signature_256 or x_hub_signature or x_gitea_signature
    
    # 读取 payload
    payload = await request.json()
    
    # 处理 webhook
    # 注意：这里需要遍历所有可能的集成配置来找到匹配的 secret
    # 简化处理：先查找所有活跃配置，逐个验证
    stmt = select(GitIntegration).where(
        GitIntegration.platform == platform,
        GitIntegration.is_active == True
    )
    result = await db.execute(stmt)
    integrations = result.scalars().all()
    
    if not integrations:
        raise HTTPException(404, f"No active integration found for platform: {platform}")
    
    # 尝试每个配置的 secret
    from src.core.crypto import decrypt_value
    from src.core.webhook_handler import verify_signature
    
    payload_bytes = await request.body()
    valid_integration = None
    
    for integration in integrations:
        try:
            stored_secret = decrypt_value(integration.webhook_secret)
            if verify_signature(payload_bytes, signature, stored_secret):
                valid_integration = integration
                break
        except Exception:
            continue
    
    if not valid_integration:
        raise HTTPException(401, "Invalid signature")
    
    # 处理事件
    if event_type == "push":
        from src.core.webhook_handler import handle_push_event
        results = await handle_push_event(db, payload, valid_integration)
        return {"status": "ok", "event": "push", "results": results}
    
    elif event_type == "pull_request":
        from src.core.webhook_handler import handle_pull_request_event
        results = await handle_pull_request_event(db, payload, valid_integration)
        return {"status": "ok", "event": "pull_request", "results": results}
    
    else:
        return {"status": "ok", "event": event_type, "results": {}}


# ─── 配置管理 API（需要认证）────────────────────────────────────────────────

@router.get("/git-integrations", response_model=List[GitIntegrationRead])
async def list_git_integrations(
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Git 集成配置列表"""
    stmt = select(GitIntegration)
    if project_id:
        stmt = stmt.where(GitIntegration.project_id == project_id)
    stmt = stmt.order_by(desc(GitIntegration.created_at))
    
    result = await db.execute(stmt)
    integrations = result.scalars().all()
    
    return [
        GitIntegrationRead(
            id=i.id,
            project_id=i.project_id,
            repo_url=i.repo_url,
            platform=i.platform,
            webhook_url=i.webhook_url,
            auto_close_issue=i.auto_close_issue,
            auto_link_pr=i.auto_link_pr,
            auto_create_issue=i.auto_create_issue,
            subscribed_events=i.subscribed_events or ["push", "pull_request"],
            is_active=i.is_active,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in integrations
    ]


@router.post("/git-integrations", response_model=GitIntegrationRead, status_code=201)
async def create_git_integration(
    data: GitIntegrationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建 Git 集成配置"""
    # 检查是否已存在
    stmt = select(GitIntegration).where(
        GitIntegration.project_id == data.project_id,
        GitIntegration.repo_url == data.repo_url,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(400, "Integration already exists for this repo")
    
    # 生成 webhook URL
    webhook_url = f"/webhook/git/{data.platform}"
    
    integration = GitIntegration(
        project_id=data.project_id,
        repo_url=data.repo_url,
        platform=data.platform,
        webhook_secret=encrypt_value(data.webhook_secret),
        webhook_url=webhook_url,
        auto_close_issue=data.auto_close_issue,
        auto_link_pr=data.auto_link_pr,
        subscribed_events=data.subscribed_events,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    
    return GitIntegrationRead(
        id=integration.id,
        project_id=integration.project_id,
        repo_url=integration.repo_url,
        platform=integration.platform,
        webhook_url=integration.webhook_url,
        auto_close_issue=integration.auto_close_issue,
        auto_link_pr=integration.auto_link_pr,
        auto_create_issue=integration.auto_create_issue,
        subscribed_events=integration.subscribed_events or ["push", "pull_request"],
        is_active=integration.is_active,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.put("/git-integrations/{integration_id}", response_model=GitIntegrationRead)
async def update_git_integration(
    integration_id: int,
    data: GitIntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新 Git 集成配置"""
    stmt = select(GitIntegration).where(GitIntegration.id == integration_id)
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(404, "Integration not found")
    
    if data.repo_url is not None:
        integration.repo_url = data.repo_url
    if data.webhook_secret is not None:
        integration.webhook_secret = encrypt_value(data.webhook_secret)
    if data.auto_close_issue is not None:
        integration.auto_close_issue = data.auto_close_issue
    if data.auto_link_pr is not None:
        integration.auto_link_pr = data.auto_link_pr
    if data.subscribed_events is not None:
        integration.subscribed_events = data.subscribed_events
    if data.is_active is not None:
        integration.is_active = data.is_active
    
    await db.commit()
    await db.refresh(integration)
    
    return GitIntegrationRead(
        id=integration.id,
        project_id=integration.project_id,
        repo_url=integration.repo_url,
        platform=integration.platform,
        webhook_url=integration.webhook_url,
        auto_close_issue=integration.auto_close_issue,
        auto_link_pr=integration.auto_link_pr,
        auto_create_issue=integration.auto_create_issue,
        subscribed_events=integration.subscribed_events or ["push", "pull_request"],
        is_active=integration.is_active,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.delete("/git-integrations/{integration_id}", status_code=204)
async def delete_git_integration(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除 Git 集成配置"""
    stmt = select(GitIntegration).where(GitIntegration.id == integration_id)
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(404, "Integration not found")
    
    await db.delete(integration)
    await db.commit()


@router.post("/git-integrations/{integration_id}/regenerate-secret")
async def regenerate_webhook_secret(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """重新生成 Webhook Secret"""
    stmt = select(GitIntegration).where(GitIntegration.id == integration_id)
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(404, "Integration not found")
    
    # 生成新的 secret
    new_secret = secrets.token_urlsafe(32)
    integration.webhook_secret = encrypt_value(new_secret)
    await db.commit()
    
    return {"secret": new_secret}


# ─── 查询关联数据 ─────────────────────────────────────────────────────────────

@router.get("/issues/{issue_id}/commits", response_model=List[CommitLinkRead])
async def get_issue_commits(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Issue 关联的 Commits"""
    stmt = select(IssueCommitLink).where(
        IssueCommitLink.issue_id == issue_id
    ).order_by(desc(IssueCommitLink.committed_at))
    
    result = await db.execute(stmt)
    links = result.scalars().all()
    
    return [
        CommitLinkRead(
            id=l.id,
            issue_id=l.issue_id,
            commit_hash=l.commit_hash,
            commit_short=l.commit_short,
            commit_message=l.commit_message,
            commit_url=l.commit_url,
            author=l.author,
            action=l.action,
            branch=l.branch,
            committed_at=l.committed_at,
            created_at=l.created_at,
        )
        for l in links
    ]


@router.get("/plans/{plan_id}/prs", response_model=List[PRPlanLinkRead])
async def get_plan_prs(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Plan 关联的 PRs"""
    stmt = select(PRPlanLink).where(
        PRPlanLink.plan_id == plan_id
    ).order_by(desc(PRPlanLink.created_at))
    
    result = await db.execute(stmt)
    links = result.scalars().all()
    
    return [
        PRPlanLinkRead(
            id=l.id,
            pr_number=l.pr_number,
            pr_title=l.pr_title,
            pr_url=l.pr_url,
            pr_status=l.pr_status,
            plan_id=l.plan_id,
            author=l.author,
            merged_at=l.merged_at,
            created_at=l.created_at,
        )
        for l in links
    ]
