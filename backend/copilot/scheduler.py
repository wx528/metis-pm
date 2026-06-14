"""
PMCopilot - 项目管理常驻智能主理人。

持有 AIAgent 实例，提供高阶业务方法（巡检、日报、问答）。
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("copilot.scheduler")


class PMCopilot:
    SYSTEM_PROMPT = """你是项目管理系统的智能主理人 PM Copilot。

你的职责：
1. 监控项目健康状态，主动发现风险
2. 回答关于项目、issue、计划的问题
3. 协助创建 issue、更新状态、创建风险告警
4. 生成项目巡检报告和日报/周报

规则：
- 使用中文回复
- 创建 issue 时 source 自动标记为 ai_agent
- 风险告警要给出明确的建议措施
- 巡检报告要包含关键指标和发现的问题
"""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None):
        from pm_copilot_engine import AIAgent

        self.model = model or os.getenv("PM_MODEL", "")
        self.base_url = base_url or os.getenv("PM_API_BASE_URL", "")
        self.api_key = api_key or os.getenv("PM_API_KEY", "")
        self.history = []

        agent_kwargs = {
            "quiet_mode": True,
            "skip_context_files": True,
            "skip_memory": True,
            "ephemeral_system_prompt": self.SYSTEM_PROMPT,
            "enabled_toolsets": ["pm"],
            "max_iterations": 25,
        }
        if self.model:
            agent_kwargs["model"] = self.model
        if self.base_url:
            agent_kwargs["base_url"] = self.base_url
        if self.api_key:
            agent_kwargs["api_key"] = self.api_key

        self.agent = AIAgent(**agent_kwargs)
        logger.info(f"PMCopilot initialized (model={self.model or 'default'})")

    def scan(self) -> str:
        result = self.agent.run_conversation(
            user_message="""执行项目健康巡检：
1. get_project_metrics() 获取整体指标
2. list_projects(status="active") 列出活跃项目
3. list_issues(priority="P0", status="open") 检查 P0 未关闭 issue
4. list_risk_alerts(status="open") 检查未解决告警
5. 如有风险，create_risk_alert() 创建告警
返回中文巡检报告。""",
            conversation_history=None,
        )
        return result.get("response", "巡检完成")

    def ask(self, question: str) -> str:
        result = self.agent.run_conversation(
            user_message=question,
            conversation_history=self.history[-20:] if self.history else None,
        )
        response = result.get("response", "")
        messages = result.get("messages", [])
        if messages:
            self.history.extend(messages)
            if len(self.history) > 40:
                self.history = self.history[-40:]
        return response

    def close(self):
        try:
            self.agent.close()
        except Exception:
            pass
