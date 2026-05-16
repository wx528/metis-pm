from fastapi import APIRouter

from src.routes import issues, milestones, plans, servers, activity_logs, auth, dashboard, projects, notifications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(issues.router, prefix="/issues", tags=["问题管理"])
api_router.include_router(milestones.router, prefix="/milestones", tags=["里程碑/分期"])
api_router.include_router(plans.router, prefix="/plans", tags=["计划管理"])
api_router.include_router(servers.router, prefix="/servers", tags=["服务器管理"])
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["活动日志"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
