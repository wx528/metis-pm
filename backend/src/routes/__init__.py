from fastapi import APIRouter

from src.routes import auth, projects, issues, plans, comments, notifications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(issues.router, prefix="/issues", tags=["问题管理"])
api_router.include_router(plans.router, prefix="/plans", tags=["计划管理"])
api_router.include_router(comments.router, prefix="/issue-comments", tags=["评论管理"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
