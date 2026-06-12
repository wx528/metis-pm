"""Git 集成相关数据模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from src.core.database import Base


class GitIntegration(Base):
    """Git 平台集成配置"""
    __tablename__ = "git_integrations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 仓库信息
    repo_url = Column(String(500), nullable=False)
    platform = Column(String(50), nullable=False)  # github / gitea / forgejo
    
    # Webhook 配置
    webhook_secret = Column(String(200), nullable=False)  # 加密存储
    webhook_url = Column(String(500), nullable=True)  # 生成的 webhook URL
    
    # 功能开关
    auto_close_issue = Column(Boolean, default=True)  # commit 自动关闭 issue
    auto_link_pr = Column(Boolean, default=True)  # PR 自动关联 plan
    auto_create_issue = Column(Boolean, default=False)  # 从 issue 模板自动创建
    
    # 事件订阅
    subscribed_events = Column(JSON, default=["push", "pull_request"])  # push / pull_request / issues
    
    # 元数据
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)


class IssueCommitLink(Base):
    """Issue 与 Commit 的关联"""
    __tablename__ = "issue_commit_links"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Commit 信息
    commit_hash = Column(String(40), nullable=False, index=True)
    commit_short = Column(String(8), nullable=False)
    commit_message = Column(Text, nullable=False)
    commit_url = Column(String(500), nullable=True)
    author = Column(String(100), nullable=False)
    author_email = Column(String(200), nullable=True)
    committed_at = Column(DateTime, nullable=False)
    
    # 关联动作
    action = Column(String(50), nullable=False)  # fix / close / resolve / reference
    branch = Column(String(200), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PRPlanLink(Base):
    """PR 与 Plan 的关联"""
    __tablename__ = "pr_plan_links"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # PR 信息
    pr_number = Column(Integer, nullable=False)
    pr_title = Column(String(500), nullable=False)
    pr_url = Column(String(500), nullable=True)
    pr_status = Column(String(50), nullable=False)  # open / merged / closed
    
    # 关联的 Plan
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    
    # 元数据
    author = Column(String(100), nullable=True)
    merged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
