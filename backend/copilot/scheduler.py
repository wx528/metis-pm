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

        # 在导入 AIAgent 前先抑制 logging 错误和跳过耗时的网络探测。
        # pm-copilot-engine 初始化时会探测 Ollama /api/show 和 models.dev，
        # 这两个调用在没有这些服务的环境下会卡住几十秒甚至超时。
        import logging as _logging
        _logging.raiseExceptions = False

        try:
            import pm_copilot_engine.agent.model_metadata as _mm
            # 用一个快速返回默认值的 stub 替换 get_model_context_length，
            # 避免它在 init_agent 阶段发起网络请求。
            _mm.get_model_context_length = lambda *a, **kw: 128000
            _mm._query_ollama_api_show = lambda *a, **kw: None
        except Exception:
            pass

        try:
            import pm_copilot_engine.agent.models_dev as _md
            # 完全跳过 fetch_models_dev 的网络访问。
            _md.fetch_models_dev = lambda *a, **kw: {}
            _md._save_disk_cache = lambda *a, **kw: None
        except Exception:
            pass

        try:
            import pm_copilot_engine.agent.process_bootstrap as _pb
            _pb._get_proxy_for_base_url = lambda base_url: None
            _pb._get_proxy_from_env = lambda: None
        except Exception:
            pass

        try:
            import pm_copilot_engine.hermes_logging as _hl
            _orig_emit = _hl._ManagedRotatingFileHandler.emit
            def _safe_emit(self, record):
                try:
                    _orig_emit(self, record)
                except OSError:
                    pass
            _hl._ManagedRotatingFileHandler.emit = _safe_emit
        except Exception:
            pass

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
        try:
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
            return result.get("final_response", "巡检完成")
        except Exception as e:
            logger.error("Copilot scan failed: %s", e)
            return "巡检失败，AI 助手暂时不可用"

    def ask(self, question: str) -> str:
        try:
            result = self.agent.run_conversation(
                user_message=question,
                conversation_history=self.history[-20:] if self.history else None,
            )
            response = result.get("final_response", "")
            messages = result.get("messages", [])
            if messages:
                self.history.extend(messages)
                if len(self.history) > 40:
                    self.history = self.history[-40:]
            return response
        except Exception as e:
            logger.error("Copilot ask failed: %s", e)
            return "抱歉，AI 助手暂时不可用"

    def close(self):
        try:
            self.agent.close()
        except Exception:
            pass
