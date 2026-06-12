"""
业务指标收集模块
使用 Prometheus Counter/Histogram/Gauge 收集关键业务事件和系统指标
"""
from prometheus_client import Counter, Histogram, Gauge

# ─── Agent 操作 ──────────────────────────────────────

agent_operations_total = Counter(
    "pm_agent_operations_total",
    "Total number of agent operations",
    ["role", "operation", "entity_type"]
)

issue_transitions_total = Counter(
    "pm_issue_transitions_total",
    "Total number of issue status transitions",
    ["from_status", "to_status"]
)

plan_approvals_total = Counter(
    "pm_plan_approvals_total",
    "Total number of plan approvals/rejections",
    ["action", "role"]
)

handovers_total = Counter(
    "pm_handovers_total",
    "Total number of handover comments",
    ["from_role", "to_role"]
)

notifications_sent_total = Counter(
    "pm_notifications_sent_total",
    "Total number of notifications sent",
    ["recipient_role", "notification_type"]
)

# ─── API 延迟 ────────────────────────────────────────

api_request_duration_seconds = Histogram(
    "pm_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ─── 当前状态 Gauge ──────────────────────────────────

current_issues_gauge = Gauge(
    "pm_current_issues",
    "Current number of issues by status",
    ["status", "priority"]
)

current_agents_online = Gauge(
    "pm_agents_online",
    "Number of agents currently online",
    ["role"]
)

# ─── 工作流步骤耗时 ──────────────────────────────────

workflow_step_duration_seconds = Histogram(
    "pm_workflow_step_duration_seconds",
    "Workflow step execution duration in seconds",
    ["step_type", "status"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0]
)

workflow_step_total = Counter(
    "pm_workflow_step_total",
    "Total number of workflow step executions",
    ["step_type", "status"]
)

# ─── MCP 工具调用延迟 ────────────────────────────────

mcp_tool_duration_seconds = Histogram(
    "pm_mcp_tool_duration_seconds",
    "MCP tool call duration in seconds",
    ["tool", "role", "success"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

mcp_tool_total = Counter(
    "pm_mcp_tool_total",
    "Total number of MCP tool calls",
    ["tool", "role", "success"]
)

# ─── 消息队列 ────────────────────────────────────────

message_queue_size = Gauge(
    "pm_message_queue_size",
    "Current number of messages in queue by status",
    ["status"]
)

message_queue_dead_letter_size = Gauge(
    "pm_message_queue_dead_letter_size",
    "Current number of messages in dead letter queue"
)

# ─── SQLite 运维指标 ─────────────────────────────────

sqlite_wal_size_bytes = Gauge(
    "pm_sqlite_wal_size_bytes",
    "SQLite WAL file size in bytes"
)

sqlite_db_size_bytes = Gauge(
    "pm_sqlite_db_size_bytes",
    "SQLite database file size in bytes"
)
