import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "registrar"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="registrar")
async def create_project(name: str, slug: str, description: str = "") -> str:
    result = await _api("POST", "/projects", json={
        "name": name, "slug": slug, "description": description,
    })
    return f"已创建项目: {result['name']} (slug: {result['slug']}, id: {result['id']})"


@registry.tool(toolset="registrar")
async def initialize_issues(project_id: int, titles: list[str]) -> str:
    created = []
    for title in titles:
        result = await _api("POST", "/issues", json={
            "title": title, "project_id": project_id, "source_role": ROLE,
        })
        created.append(f"  #{result['id']} {result['title']}")
    return f"已创建 {len(created)} 个 Issue:\n" + "\n".join(created)


@registry.tool(toolset="registrar")
async def get_project_context(project_id: int) -> str:
    project = await _api("GET", f"/projects/{project_id}")
    issues = await _api("GET", "/issues", params={"project_id": project_id, "limit": 5})
    lines = [
        f"项目: {project['name']}",
        f"Issue 总数: {project.get('issue_count', 0)} | 进行中: {project.get('open_issue_count', 0)}",
        f"Plan 数: {project.get('plan_count', 0)}",
    ]
    items = issues.get("items", [])
    if items:
        lines.append("\n最近 Issue:")
        for i in items:
            lines.append(f"  #{i['id']} [{i['priority']}] {i['title']} ({i['status']})")
    return "\n".join(lines)


def register_tools():
    pass
