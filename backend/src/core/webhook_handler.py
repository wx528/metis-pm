"""Git Webhook 处理器"""
import hmac
import hashlib
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.git_integration import GitIntegration, IssueCommitLink, PRPlanLink
from src.models.issue import Issue, IssueStatus
from src.models.plan import Plan, PlanStatus
from src.models.activity_log import ActivityLog
from src.core.crypto import decrypt_value

logger = logging.getLogger(__name__)

# Commit message 中匹配 issue 引用的正则
# 支持: fix #123, fixes #123, close #123, closes #123, resolve #123, resolves #123, ref #123
ISSUE_PATTERN = re.compile(
    r"(?:fix|fixes|close|closes|resolve|resolves|ref|refs)\s+#(\d+)",
    re.IGNORECASE
)

# 动作类型映射
ACTION_MAP = {
    "fix": "fix",
    "fixes": "fix",
    "close": "close",
    "closes": "close",
    "resolve": "resolve",
    "resolves": "resolve",
    "ref": "reference",
    "refs": "reference",
}

# 自动关闭 issue 的动作
AUTO_CLOSE_ACTIONS = {"fix", "close", "resolve"}


def verify_signature(payload: bytes, signature: Optional[str], secret: str) -> bool:
    """验证 Webhook 签名（支持 GitHub/Gitea/Forgejo）"""
    if not signature:
        return False
    
    # GitHub 格式: sha256=xxx 或 sha1=xxx
    if signature.startswith("sha256="):
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    if signature.startswith("sha1="):
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha1
        ).hexdigest()
        return hmac.compare_digest(f"sha1={expected}", signature)
    
    # Gitea/Forgejo 可能直接用 hex
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_commit_message(message: str) -> list[tuple[int, str]]:
    """解析 commit message，提取 issue 引用和动作"""
    results = []
    for match in ISSUE_PATTERN.finditer(message):
        keyword = match.group(0).split()[0].lower()
        issue_id = int(match.group(1))
        action = ACTION_MAP.get(keyword, "reference")
        results.append((issue_id, action))
    return results


async def handle_push_event(
    db: AsyncSession,
    payload: dict,
    integration: GitIntegration
) -> dict:
    """处理 push 事件"""
    results = {
        "commits_processed": 0,
        "issues_linked": 0,
        "issues_closed": 0,
    }
    
    commits = payload.get("commits", [])
    repo_name = payload.get("repository", {}).get("full_name", "")
    branch = payload.get("ref", "").replace("refs/heads/", "")
    
    for commit in commits:
        commit_hash = commit.get("id", "")
        commit_message = commit.get("message", "")
        commit_url = commit.get("url", "")
        author = commit.get("author", {})
        author_name = author.get("name", "unknown")
        author_email = author.get("email", "")
        committed_at = datetime.fromisoformat(
            commit.get("timestamp", datetime.now(timezone.utc).isoformat())
        )
        
        # 解析 commit message
        references = parse_commit_message(commit_message)
        
        for issue_id, action in references:
            # 查找 issue
            stmt = select(Issue).where(
                Issue.id == issue_id,
                Issue.project_id == integration.project_id
            )
            result = await db.execute(stmt)
            issue = result.scalar_one_or_none()
            
            if not issue:
                logger.warning(f"Issue #{issue_id} not found in project {integration.project_id}")
                continue
            
            # 创建关联记录
            link = IssueCommitLink(
                issue_id=issue_id,
                project_id=integration.project_id,
                commit_hash=commit_hash,
                commit_short=commit_hash[:8],
                commit_message=commit_message.split("\n")[0][:500],
                commit_url=commit_url,
                author=author_name,
                author_email=author_email,
                committed_at=committed_at,
                action=action,
                branch=branch,
            )
            db.add(link)
            results["issues_linked"] += 1
            
            # 自动关闭 issue
            if integration.auto_close_issue and action in AUTO_CLOSE_ACTIONS:
                if issue.status not in [IssueStatus.CLOSED, IssueStatus.CANCELLED]:
                    old_status = issue.status.value
                    issue.status = IssueStatus.CLOSED
                    issue.closed_at = datetime.now(timezone.utc)
                    
                    # 记录活动日志
                    activity = ActivityLog(
                        project_id=integration.project_id,
                        entity_type="issue",
                        entity_id=issue_id,
                        action="closed_by_commit",
                        old_value={"status": old_status},
                        new_value={"status": "closed", "commit": commit_hash[:8]},
                        actor=author_name,
                    )
                    db.add(activity)
                    results["issues_closed"] += 1
            
            # 记录引用活动（非关闭动作）
            elif action == "reference":
                activity = ActivityLog(
                    project_id=integration.project_id,
                    entity_type="issue",
                    entity_id=issue_id,
                    action="referenced_by_commit",
                    new_value={"commit": commit_hash[:8], "message": commit_message.split("\n")[0][:100]},
                    actor=author_name,
                )
                db.add(activity)
        
        results["commits_processed"] += 1
    
    await db.commit()
    return results


async def handle_pull_request_event(
    db: AsyncSession,
    payload: dict,
    integration: GitIntegration
) -> dict:
    """处理 pull_request 事件"""
    results = {
        "pr_linked": False,
        "plans_updated": 0,
    }
    
    action = payload.get("action")  # opened, closed, merged, etc.
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title", "")
    pr_body = pr.get("body", "")
    pr_url = pr.get("html_url", "")
    pr_status = "merged" if pr.get("merged") else ("closed" if pr.get("state") == "closed" else "open")
    author = pr.get("user", {}).get("login", "unknown")
    merged_at = None
    if pr.get("merged_at"):
        merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
    
    # 从 PR 标题和描述中提取 plan 引用
    # 支持: plan #123, Plan-123, #plan-123
    plan_pattern = re.compile(r"(?:plan\s*#?|Plan-|#plan-)(\d+)", re.IGNORECASE)
    plan_ids = set()
    for text in [pr_title, pr_body]:
        for match in plan_pattern.finditer(text):
            plan_ids.add(int(match.group(1)))
    
    # 创建/更新 PR-Plan 关联
    for plan_id in plan_ids:
        # 查找 plan
        stmt = select(Plan).where(
            Plan.id == plan_id,
            Plan.project_id == integration.project_id
        )
        result = await db.execute(stmt)
        plan = result.scalar_one_or_none()
        
        if not plan:
            logger.warning(f"Plan #{plan_id} not found in project {integration.project_id}")
            continue
        
        # 查找或创建关联
        stmt = select(PRPlanLink).where(
            PRPlanLink.project_id == integration.project_id,
            PRPlanLink.pr_number == pr_number,
            PRPlanLink.plan_id == plan_id
        )
        result = await db.execute(stmt)
        link = result.scalar_one_or_none()
        
        if not link:
            link = PRPlanLink(
                project_id=integration.project_id,
                pr_number=pr_number,
                pr_title=pr_title[:500],
                pr_url=pr_url,
                pr_status=pr_status,
                plan_id=plan_id,
                author=author,
                merged_at=merged_at,
            )
            db.add(link)
        else:
            link.pr_status = pr_status
            if merged_at:
                link.merged_at = merged_at
        
        # PR 合并时更新 plan 状态
        if integration.auto_link_pr and action == "closed" and pr.get("merged"):
            if plan.status == PlanStatus.IN_PROGRESS:
                plan.status = PlanStatus.COMPLETED
                results["plans_updated"] += 1
                
                # 记录活动日志
                activity = ActivityLog(
                    project_id=integration.project_id,
                    entity_type="plan",
                    entity_id=plan_id,
                    action="completed_by_pr",
                    new_value={"pr_number": pr_number, "pr_title": pr_title[:100]},
                    actor=author,
                )
                db.add(activity)
        
        results["pr_linked"] = True
    
    await db.commit()
    return results


async def process_webhook(
    db: AsyncSession,
    platform: str,
    event_type: str,
    payload: dict,
    signature: Optional[str],
    secret: str,
    raw_payload: Optional[bytes] = None,
) -> dict:
    """处理 webhook 事件的主入口

    Args:
        raw_payload: 原始 HTTP body 字节，用于签名验证。
                     如果不提供，将退化为 ``json.dumps(payload, sort_keys=True).encode()``。
                     GitHub/Gitea 的签名是基于 HTTP body 原始字节计算的，
                     不能使用 str(dict) 这种会产生不同输出的编码方式。
    """

    # 根据平台获取集成配置
    # 从 payload 中提取仓库信息
    repo_url = ""
    if platform == "github":
        repo_url = payload.get("repository", {}).get("html_url", "")
    elif platform in ["gitea", "forgejo"]:
        repo_url = payload.get("repository", {}).get("html_url", "")

    # 查找匹配的集成配置
    stmt = select(GitIntegration).where(
        GitIntegration.repo_url == repo_url,
        GitIntegration.platform == platform,
        GitIntegration.is_active == True
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()

    if not integration:
        # 尝试通过 project_id 查找（如果 payload 中有）
        project_id = payload.get("project_id")
        if project_id:
            stmt = select(GitIntegration).where(
                GitIntegration.project_id == project_id,
                GitIntegration.platform == platform,
                GitIntegration.is_active == True
            )
            result = await db.execute(stmt)
            integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(404, f"No active integration found for repo: {repo_url}")

    # 验证签名：必须用原始 HTTP body 字节，不能用 str(dict) 重新编码
    stored_secret = decrypt_value(integration.webhook_secret)
    if raw_payload is None:
        import json as _json
        raw_payload = _json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if not verify_signature(raw_payload, signature, stored_secret):
        raise HTTPException(401, "Invalid signature")

    # 检查事件是否在订阅列表中
    if event_type not in (integration.subscribed_events or []):
        return {"status": "ignored", "reason": "event not subscribed"}

    # 处理事件
    if event_type == "push":
        results = await handle_push_event(db, payload, integration)
        return {"status": "ok", "event": "push", "results": results}

    elif event_type == "pull_request":
        results = await handle_pull_request_event(db, payload, integration)
        return {"status": "ok", "event": "pull_request", "results": results}

    else:
        return {"status": "ok", "event": event_type, "results": {}}
