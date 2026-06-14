"""
A2A Agent 注册表：管理已发现的外部 Agent 及其能力

Agent Card 规范 (A2A v1.0):
  每个 A2A Agent 通过 /.well-known/agent-card.json 发布能力描述。
  PM 系统维护一个本地注册表，记录已发现的 Agent 及其端点。

注册方式：
  1. 自动发现：扫描已知端点的 Agent Card
  2. 手动注册：通过 API 或环境变量添加
  3. MCP 连接时注册：外部 Agent 通过 MCP 连接时自动注册
"""
import logging
import os
import json
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("a2a.registry")


@dataclass
class AgentSkill:
    """Agent 能力描述"""
    id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class AgentCard:
    """A2A Agent Card — 描述外部 Agent 的身份和能力"""
    agent_id: str
    name: str
    description: str = ""
    url: str = ""                          # A2A 端点 URL
    card_url: str = ""                     # Agent Card JSON URL
    skills: list[AgentSkill] = field(default_factory=list)
    framework: str = ""                    # langchain / crewai / autogen / custom
    version: str = "1.0"
    status: str = "active"                 # active / inactive / error
    last_seen: str = ""
    auth_type: str = ""                    # none / api_key / oauth2
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AgentCard":
        skills_data = data.pop("skills", [])
        skills = [AgentSkill(**s) for s in skills_data]
        return cls(skills=skills, **data)

    @classmethod
    def from_card_json(cls, card_data: dict, url: str = "") -> "AgentCard":
        """从 A2A Agent Card JSON 解析"""
        skills = []
        for s in card_data.get("skills", []):
            skills.append(AgentSkill(
                id=s.get("id", ""),
                name=s.get("name", ""),
                description=s.get("description", ""),
                tags=s.get("tags", []),
            ))
        return cls(
            agent_id=card_data.get("id", card_data.get("name", "unknown")),
            name=card_data.get("name", "unknown"),
            description=card_data.get("description", ""),
            url=url or card_data.get("url", ""),
            card_url=card_data.get("card_url", ""),
            skills=skills,
            framework=card_data.get("framework", ""),
            version=card_data.get("version", "1.0"),
            status="active",
            last_seen=datetime.now(timezone.utc).isoformat(),
            auth_type=card_data.get("auth_type", ""),
            metadata=card_data.get("metadata", {}),
        )


class AgentRegistry:
    """
    外部 Agent 注册表

    管理 PM 系统已知的所有外部 A2A Agent。
    支持按能力查找 Agent（如"谁能处理 P0 issue？"）。
    """

    def __init__(self):
        self._agents: dict[str, AgentCard] = {}

    def register(self, card: AgentCard) -> None:
        """注册或更新一个外部 Agent"""
        card.last_seen = datetime.now(timezone.utc).isoformat()
        self._agents[card.agent_id] = card
        logger.info("Agent registered: %s (%s) at %s", card.name, card.agent_id, card.url)

    def unregister(self, agent_id: str) -> bool:
        """注销一个外部 Agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("Agent unregistered: %s", agent_id)
            return True
        return False

    def get(self, agent_id: str) -> Optional[AgentCard]:
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentCard]:
        return list(self._agents.values())

    def list_active(self) -> list[AgentCard]:
        return [a for a in self._agents.values() if a.status == "active"]

    def find_by_skill(self, skill_tag: str) -> list[AgentCard]:
        """按能力标签查找 Agent"""
        results = []
        for agent in self._agents.values():
            if agent.status != "active":
                continue
            for skill in agent.skills:
                if skill_tag.lower() in [t.lower() for t in skill.tags] or skill_tag.lower() in skill.name.lower():
                    results.append(agent)
                    break
        return results

    def find_by_capability(self, capability: str) -> list[AgentCard]:
        """
        按能力描述查找 Agent（模糊匹配）

        capability 示例: "issue-handling", "risk-analysis", "code-review"
        """
        results = []
        capability_lower = capability.lower()
        for agent in self._agents.values():
            if agent.status != "active":
                continue
            # 检查 name, description, skill tags
            searchable = (
                agent.name.lower() + " " +
                agent.description.lower() + " " +
                " ".join(s.name.lower() + " " + s.description.lower() + " ".join(s.tags) for s in agent.skills)
            )
            if capability_lower in searchable:
                results.append(agent)
        return results

    def mark_inactive(self, agent_id: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].status = "inactive"

    def mark_error(self, agent_id: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].status = "error"


# 全局单例
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def init_registry_from_env() -> AgentRegistry:
    """
    从环境变量初始化注册表

    环境变量格式:
      A2A_AGENTS=agent1:http://host1:8001,agent2:http://host2:8002

    每个 Agent 会在启动时尝试获取其 Agent Card。
    """
    registry = get_registry()
    agents_str = os.getenv("A2A_AGENTS", "")
    if not agents_str:
        return registry

    for entry in agents_str.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        name, url = entry.split(":", 1)
        url = url.strip()
        name = name.strip()
        card = AgentCard(
            agent_id=name,
            name=name,
            url=url,
            card_url=f"{url}/.well-known/agent-card.json",
            status="active",
        )
        registry.register(card)
        logger.info("Registered agent from env: %s at %s", name, url)

    return registry
