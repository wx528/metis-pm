import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000/api/v1')
API_KEY = os.getenv('API_KEY', 'metis-pm-default-key-change-me')
ROLE = 'tester'

HEADERS = {'X-API-Key': API_KEY, 'Content-Type': 'application/json'}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f'{BACKEND_URL}{path}', headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset='tester')
async def report_bug(project_id: int, title: str, description: str = '', priority: str = 'P2') -> str:
    result = await _api('POST', '/issues', json={
        'title': title, 'description': description,
        'project_id': project_id, 'priority': priority,
        'issue_type': 'bug', 'source_role': ROLE,
    })
    return f"已报告 Bug #{result['id']}: {result['title']}"


@registry.tool(toolset='tester')
async def request_feature(project_id: int, title: str, description: str = '') -> str:
    result = await _api('POST', '/issues', json={
        'title': title, 'description': description,
        'project_id': project_id, 'issue_type': 'feature',
        'source_role': ROLE,
    })
    return f"已创建功能请求 #{result['id']}: {result['title']}"


@registry.tool(toolset='tester')
async def verify_issue(issue_id: int, passed: bool, comment: str = '') -> str:
    if passed:
        await _api('PUT', f'/issues/{issue_id}', json={'status': 'closed'})
        await _api('POST', f'/issues/{issue_id}/comments', json={
            'content': f'验证通过。{comment}', 'author_role': ROLE,
        })
        return f'Issue #{issue_id} 验证通过，已关闭'
    else:
        await _api('PUT', f'/issues/{issue_id}', json={'status': 'in_progress'})
        await _api('POST', f'/issues/{issue_id}/comments', json={
            'content': f'验证未通过。{comment}', 'author_role': ROLE,
        })
        return f'Issue #{issue_id} 验证未通过，已退回'


@registry.tool(toolset='tester')
async def list_my_issues(project_id: int | None = None) -> str:
    params = {'source_role': ROLE}
    if project_id:
        params['project_id'] = project_id
    result = await _api('GET', '/issues', params=params)
    items = result.get('items', [])
    if not items:
        return '你还没有创建过 Issue。'
    lines = [f"你创建的 Issue ({result['total']}):"]
    for i in items:
        lines.append(f"  #{i['id']} [{i['priority']}] {i['title']} ({i['status']})")
    return '\n'.join(lines)


def register_tools():
    pass
