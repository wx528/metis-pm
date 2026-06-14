"""
A2A (Agent-to-Agent) 集成模块

PM 系统通过 A2A 协议与外部 Agent 双向通信：
- A2A Client: 主动向外部 Agent 委派任务（如 P0 issue 处理、风险分析）
- A2A Server: 暴露 PM 系统能力给外部 Agent 调用
- Agent Registry: 管理已发现的外部 Agent 及其能力

与 MCP 的关系：
  MCP = Agent ↔ Tool（PM 系统作为工具提供者）
  A2A = Agent ↔ Agent（PM 系统作为对等协作方）

协议参考: https://github.com/a2aproject/A2A (Google A2A v1.0)
"""
