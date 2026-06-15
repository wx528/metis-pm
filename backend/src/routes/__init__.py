from fastapi import APIRouter
import os

from src.routes import issues, milestones, plans, servers, activity_logs, auth, dashboard, projects, notifications, stats, workflows, agent_memory, project_registrations, agent_status, monitoring, comments, feedback, git_webhook, graph, risk_alerts, copilot, external_api

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(graph.router, prefix="/projects/{slug}/graph", tags=["Graph View"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(issues.router, prefix="/issues", tags=["问题管理"])
api_router.include_router(milestones.router, prefix="/milestones", tags=["里程碑/分期"])
api_router.include_router(plans.router, prefix="/plans", tags=["计划管理"])
api_router.include_router(servers.router, prefix="/servers", tags=["服务器管理"])
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["活动日志"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计分析"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流"])
api_router.include_router(agent_memory.router, prefix="/agent-memories", tags=["Agent记忆"])
api_router.include_router(project_registrations.router, prefix="/project-registrations", tags=["项目登记"])
api_router.include_router(agent_status.router, prefix="/dashboard", tags=["Agent状态"])
api_router.include_router(monitoring.public_router, prefix="/monitoring", tags=["系统监控"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["系统监控"])
api_router.include_router(comments.router, prefix="/issue-comments", tags=["评论管理"])
api_router.include_router(feedback.router, prefix="/feedbacks", tags=["意见箱"])
api_router.include_router(risk_alerts.router, prefix="/risk-alerts", tags=["风险告警"])

# Copilot 路由：status 端点始终注册，其余仅在启用时注册
api_router.include_router(copilot.status_router, prefix="/copilot", tags=["Copilot"])
if os.getenv("PM_COPILOT_ENABLED", "false").lower() == "true":
    api_router.include_router(copilot.router, prefix="/copilot", tags=["Copilot"])

# A2A 路由：始终注册在根路径（不在 /api/v1 下），符合 A2A 协议规范
# 由 main.py 直接 include 到 app，本文件不重复 include。

# A2A 管理 API
from src.a2a.api import router as a2a_api_router
api_router.include_router(a2a_api_router, prefix="/a2a", tags=["A2A管理"])

api_router.include_router(git_webhook.router, prefix="", tags=["Git Webhook"])

# 外部 API：Bearer Token 认证，供外部 Agent 提交产品意见/Issue
api_router.include_router(external_api.router, prefix="/external", tags=["外部API"])
