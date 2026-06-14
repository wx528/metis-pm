"""
PM 工具实现 + 注册到 pm-copilot-engine registry。

工具列表：
- list_projects: 列出项目概览
- get_project_detail: 获取项目详情（含 issue 列表）
- list_issues: 查询 issue 列表
- get_issue_detail: 获取 issue 详情
- create_issue: 创建 issue
- update_issue_status: 更新 issue 状态
- list_risk_alerts: 列出风险告警
- create_risk_alert: 创建风险告警
- get_project_metrics: 获取项目健康指标
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("copilot.tools")

# 模块级同步引擎，复用避免资源泄漏
_sync_engine = None
_sync_session_factory = None


def _get_sync_session():
    """获取同步数据库 session（引擎工具调用是同步的）

    复用模块级引擎实例，避免每次调用都 create_engine。
    """
    global _sync_engine, _sync_session_factory
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy import create_engine
    from src.settings import settings

    if _sync_engine is None:
        url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
        _sync_engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if "sqlite" in url else {},
            pool_pre_ping=True,
        )
        _sync_session_factory = sessionmaker(bind=_sync_engine)

    return _sync_session_factory()


def _serialize_issue(issue):
    return {
        "id": issue.id,
        "title": issue.title,
        "status": str(issue.status),
        "priority": str(issue.priority),
        "issue_type": str(issue.issue_type),
        "labels": issue.labels,
        "milestone_id": issue.milestone_id,
        "parent_id": issue.parent_id,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }


def _serialize_project(project):
    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "status": str(project.status),
        "description": project.description,
    }


def list_projects(status: str = "active", **kwargs) -> str:
    from src.models.project import Project
    session = _get_sync_session()
    try:
        q = session.query(Project)
        if status != "all":
            q = q.filter(Project.status == status)
        projects = q.all()
        return json.dumps({
            "count": len(projects),
            "projects": [_serialize_project(p) for p in projects],
        }, ensure_ascii=False, indent=2)
    finally:
        session.close()


def get_project_detail(project_id: int = 0, **kwargs) -> str:
    from src.models.project import Project
    from src.models.issue import Issue
    session = _get_sync_session()
    try:
        project = session.query(Project).get(project_id)
        if not project:
            return json.dumps({"error": f"Project {project_id} not found"})
        issues = session.query(Issue).filter(Issue.project_id == project_id).all()
        return json.dumps({
            "project": _serialize_project(project),
            "issue_count": len(issues),
            "issues": [_serialize_issue(i) for i in issues[:50]],
        }, ensure_ascii=False, indent=2)
    finally:
        session.close()


def list_issues(project_id: int = 0, status: str = "", priority: str = "", limit: int = 20, **kwargs) -> str:
    from src.models.issue import Issue, IssueStatus, IssuePriority
    session = _get_sync_session()
    try:
        q = session.query(Issue)
        if project_id:
            q = q.filter(Issue.project_id == project_id)
        if status:
            try:
                q = q.filter(Issue.status == IssueStatus(status))
            except ValueError:
                pass
        if priority:
            try:
                q = q.filter(Issue.priority == IssuePriority(priority))
            except ValueError:
                pass
        issues = q.order_by(Issue.created_at.desc()).limit(limit).all()
        return json.dumps({
            "count": len(issues),
            "issues": [_serialize_issue(i) for i in issues],
        }, ensure_ascii=False, indent=2)
    finally:
        session.close()


def get_issue_detail(issue_id: int = 0, **kwargs) -> str:
    from src.models.issue import Issue
    session = _get_sync_session()
    try:
        issue = session.query(Issue).get(issue_id)
        if not issue:
            return json.dumps({"error": f"Issue {issue_id} not found"})
        return json.dumps(_serialize_issue(issue), ensure_ascii=False, indent=2)
    finally:
        session.close()


def create_issue(title: str = "", project_id: int = 0, priority: str = "P2",
                 issue_type: str = "task", description: str = "", **kwargs) -> str:
    from src.models.issue import Issue, IssuePriority, IssueType, IssueSource
    session = _get_sync_session()
    try:
        issue = Issue(
            title=title,
            project_id=project_id or None,
            priority=IssuePriority(priority) if priority in [e.value for e in IssuePriority] else IssuePriority.P2,
            issue_type=IssueType(issue_type) if issue_type in [e.value for e in IssueType] else IssueType.TASK,
            description=description or None,
            source=IssueSource.AI_AGENT,
            created_by="copilot",
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return json.dumps({"success": True, "issue_id": issue.id, "title": issue.title}, ensure_ascii=False)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        session.close()


def update_issue_status(issue_id: int = 0, status: str = "", **kwargs) -> str:
    from src.models.issue import Issue, IssueStatus
    session = _get_sync_session()
    try:
        issue = session.query(Issue).get(issue_id)
        if not issue:
            return json.dumps({"error": f"Issue {issue_id} not found"})
        old_status = str(issue.status)
        valid = [e.value for e in IssueStatus]
        if status not in valid:
            return json.dumps({"error": f"Invalid status. Valid: {valid}"})
        issue.status = IssueStatus(status)
        if status == "closed":
            issue.closed_at = datetime.now(timezone.utc)
        session.commit()
        return json.dumps({"success": True, "old_status": old_status, "new_status": status}, ensure_ascii=False)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        session.close()


def list_risk_alerts(status: str = "", level: str = "", limit: int = 20, **kwargs) -> str:
    from src.models.risk_alert import RiskAlert, RiskAlertStatus, RiskAlertLevel
    session = _get_sync_session()
    try:
        q = session.query(RiskAlert)
        if status:
            try:
                q = q.filter(RiskAlert.status == RiskAlertStatus(status))
            except ValueError:
                pass
        if level:
            try:
                q = q.filter(RiskAlert.level == RiskAlertLevel(level))
            except ValueError:
                pass
        alerts = q.order_by(RiskAlert.created_at.desc()).limit(limit).all()
        return json.dumps({
            "count": len(alerts),
            "alerts": [{
                "id": a.id, "title": a.title, "level": str(a.level),
                "status": str(a.status), "source": str(a.source),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            } for a in alerts],
        }, ensure_ascii=False, indent=2)
    finally:
        session.close()


def create_risk_alert(title: str = "", description: str = "", level: str = "medium",
                      project_id: int = 0, suggested_action: str = "", **kwargs) -> str:
    from src.models.risk_alert import RiskAlert, RiskAlertLevel, RiskAlertSource
    session = _get_sync_session()
    try:
        alert = RiskAlert(
            title=title,
            description=description or None,
            level=RiskAlertLevel(level) if level in [e.value for e in RiskAlertLevel] else RiskAlertLevel.MEDIUM,
            source=RiskAlertSource.COPILOT,
            project_id=project_id or None,
            suggested_action=suggested_action or None,
            created_by="copilot",
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return json.dumps({"success": True, "alert_id": alert.id}, ensure_ascii=False)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        session.close()


def get_project_metrics(**kwargs) -> str:
    from src.models.project import Project
    from src.models.issue import Issue, IssueStatus, IssuePriority
    from src.models.risk_alert import RiskAlert, RiskAlertStatus
    session = _get_sync_session()
    try:
        active_projects = session.query(Project).filter(Project.status == "active").count()
        open_issues = session.query(Issue).filter(Issue.status == IssueStatus.OPEN).count()
        in_progress = session.query(Issue).filter(Issue.status == IssueStatus.IN_PROGRESS).count()
        p0_open = session.query(Issue).filter(
            Issue.priority == IssuePriority.P0,
            Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS])
        ).count()
        open_alerts = session.query(RiskAlert).filter(
            RiskAlert.status.in_([RiskAlertStatus.OPEN, RiskAlertStatus.ACKNOWLEDGED])
        ).count()
        return json.dumps({
            "active_projects": active_projects,
            "open_issues": open_issues,
            "in_progress_issues": in_progress,
            "p0_open": p0_open,
            "open_risk_alerts": open_alerts,
        }, ensure_ascii=False, indent=2)
    finally:
        session.close()


def register_all_tools():
    """将所有 PM 工具注册到引擎的 registry。"""
    import inspect
    from pm_copilot_engine import registry, TOOLSETS

    tools = [
        ("list_projects", "列出所有项目概览（名称、状态、描述）",
         {"type": "object", "properties": {
             "status": {"type": "string", "enum": ["active", "archived", "all"], "default": "active"}
         }}, list_projects, "📁"),
        ("get_project_detail", "获取指定项目的详细信息（含 issue 列表）",
         {"type": "object", "properties": {
             "project_id": {"type": "integer"}
         }, "required": ["project_id"]}, get_project_detail, "📋"),
        ("list_issues", "查询 issue 列表（支持按项目、状态、优先级筛选）",
         {"type": "object", "properties": {
             "project_id": {"type": "integer", "default": 0},
             "status": {"type": "string", "default": ""},
             "priority": {"type": "string", "default": ""},
             "limit": {"type": "integer", "default": 20}
         }}, list_issues, "📝"),
        ("get_issue_detail", "获取指定 issue 的详细信息",
         {"type": "object", "properties": {
             "issue_id": {"type": "integer"}
         }, "required": ["issue_id"]}, get_issue_detail, "🔍"),
        ("create_issue", "创建新 issue（来源自动标记为 ai_agent）",
         {"type": "object", "properties": {
             "title": {"type": "string"},
             "project_id": {"type": "integer", "default": 0},
             "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"], "default": "P2"},
             "issue_type": {"type": "string", "enum": ["bug", "feature", "task", "improvement", "documentation", "idea"], "default": "task"},
             "description": {"type": "string", "default": ""}
         }, "required": ["title"]}, create_issue, "➕"),
        ("update_issue_status", "更新 issue 状态",
         {"type": "object", "properties": {
             "issue_id": {"type": "integer"},
             "status": {"type": "string", "enum": ["open", "in_progress", "review", "deferred", "closed", "cancelled"]}
         }, "required": ["issue_id", "status"]}, update_issue_status, "✏️"),
        ("list_risk_alerts", "列出风险告警",
         {"type": "object", "properties": {
             "status": {"type": "string", "default": ""},
             "level": {"type": "string", "default": ""},
             "limit": {"type": "integer", "default": 20}
         }}, list_risk_alerts, "🚨"),
        ("create_risk_alert", "创建风险告警",
         {"type": "object", "properties": {
             "title": {"type": "string"},
             "description": {"type": "string", "default": ""},
             "level": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
             "project_id": {"type": "integer", "default": 0},
             "suggested_action": {"type": "string", "default": ""}
         }, "required": ["title"]}, create_risk_alert, "⚠️"),
        ("get_project_metrics", "获取项目整体健康指标快照",
         {"type": "object", "properties": {}}, get_project_metrics, "📊"),
    ]

    def _make_handler(fn):
        """创建安全的 handler 适配器，只传递函数接受的参数。"""
        sig = inspect.signature(fn)
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if accepts_kwargs:
            return lambda args, **kw: fn(**args, **kw)
        valid_params = set(sig.parameters.keys())
        return lambda args, **kw: fn(**{k: v for k, v in args.items() if k in valid_params})

    for name, desc, schema, handler, emoji in tools:
        registry.register(
            name=name,
            toolset="pm",
            schema={"name": name, "description": desc, "parameters": schema},
            handler=_make_handler(handler),
            emoji=emoji,
        )

    TOOLSETS["pm"] = {
        "description": "项目管理系统工具集",
        "tools": [t[0] for t in tools],
        "includes": [],
    }

    logger.info(f"Registered {len(tools)} PM tools to engine registry")
