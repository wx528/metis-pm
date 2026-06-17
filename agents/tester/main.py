import os
from pm_copilot_engine import AIAgent, registry
from tools import register_tools

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "tester"

register_tools()

agent = AIAgent(
    model=os.getenv("PM_MODEL", "gpt-4o"),
    base_url=os.getenv("PM_API_BASE_URL"),
    api_key=os.getenv("PM_API_KEY"),
    system_prompt=open("system_prompt.md").read(),
    enabled_toolsets=["tester"],
)

if __name__ == "__main__":
    agent.run()
