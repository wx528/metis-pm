"""
业务指标收集模块
使用 Prometheus Counter/Histogram 收集关键业务事件
"""
from prometheus_client import Counter, Histogram, Gauge

# Agent 操作计数器
agent_operations_total = Counter(
    "pm_agent_operations_total",
    "Total number of agent operations",
    ["role", "operation", "entity_type"]
)

# Issue 状态流转计数器
issue_transitions_total = Counter(
    "pm_issue_transitions_total",
    "Total number of issue status transitions",
    ["from_status", "to_status"]
)

# Plan 审批计数器
plan_approvals_total = Counter(
    "pm_plan_approvals_total",
    "Total number of plan approvals/rejections",
    ["action", "role"]
)

# API 响应时间直方图（按端点分组）
api_request_duration_seconds = Histogram(
    "pm_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# 当前活跃 Issue 数量
current_issues_gauge = Gauge(
    "pm_current_issues",
    "Current number of issues by status",
    ["status", "priority"]
)

# 当前 Agent 在线状态
current_agents_online = Gauge(
    "pm_agents_online",
    "Number of agents currently online",
    ["role"]
)

# Handover 评论计数器
handovers_total = Counter(
    "pm_handovers_total",
    "Total number of handover comments",
    ["from_role", "to_role"]
)

# 通知发送计数器
notifications_sent_total = Counter(
    "pm_notifications_sent_total",
    "Total number of notifications sent",
    ["recipient_role", "notification_type"]
)
