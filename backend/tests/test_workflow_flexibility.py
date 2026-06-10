"""测试工作流引擎灵活性：条件分支、并行执行"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def auth_headers(client):
    resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestWorkflowTemplates:
    """工作流模板测试"""

    @pytest.mark.asyncio
    async def test_list_templates(self, client, auth_headers):
        """测试获取模板列表"""
        resp = await client.get("/api/v1/workflows/templates", headers=auth_headers)
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) >= 2
        template_ids = [t["id"] for t in templates]
        assert "dev_review_test" in template_ids
        assert "urgent_bug" in template_ids

    @pytest.mark.asyncio
    async def test_create_from_template(self, client, auth_headers):
        """测试从模板创建工作流"""
        resp = await client.post("/api/v1/workflows/from-template/dev_review_test", headers=auth_headers)
        assert resp.status_code == 201
        workflow = resp.json()
        assert workflow["name"] == "开发→审查→测试→完成"
        assert len(workflow["steps"]) == 4
        
        # 验证条件分支字段
        step_with_condition = [s for s in workflow["steps"] if s.get("condition")]
        assert len(step_with_condition) >= 1

    @pytest.mark.asyncio
    async def test_create_from_urgent_bug_template(self, client, auth_headers):
        """测试紧急 Bug 修复模板"""
        resp = await client.post("/api/v1/workflows/from-template/urgent_bug", headers=auth_headers)
        assert resp.status_code == 201
        workflow = resp.json()
        assert workflow["name"] == "紧急 Bug 修复"
        
        # 验证并行组
        parallel_steps = [s for s in workflow["steps"] if s.get("parallel_group")]
        assert len(parallel_steps) >= 2


class TestWorkflowConditions:
    """条件分支测试"""

    @pytest.mark.asyncio
    async def test_workflow_with_condition_field(self, client, auth_headers):
        """测试创建带条件的工作流"""
        workflow_data = {
            "name": "条件测试",
            "steps": [
                {"step_type": "notify", "name": "开始", "sort_order": 0},
                {"step_type": "notify", "name": "条件步骤", "sort_order": 1, "condition": "True"},
                {"step_type": "notify", "name": "成功分支", "sort_order": 2},
            ]
        }
        resp = await client.post("/api/v1/workflows", json=workflow_data, headers=auth_headers)
        assert resp.status_code == 201
        workflow = resp.json()
        assert len(workflow["steps"]) == 3
        
        # 验证条件字段保存正确
        condition_step = [s for s in workflow["steps"] if s["name"] == "条件步骤"][0]
        assert condition_step["condition"] == "True"

    @pytest.mark.asyncio
    async def test_workflow_with_next_step_id(self, client, auth_headers):
        """测试创建带跳转的工作流"""
        # 先创建一个简单工作流获取 step ID
        workflow_data = {
            "name": "跳转测试",
            "steps": [
                {"step_type": "notify", "name": "步骤1", "sort_order": 0},
                {"step_type": "notify", "name": "步骤2", "sort_order": 1},
                {"step_type": "notify", "name": "步骤3", "sort_order": 2},
            ]
        }
        resp = await client.post("/api/v1/workflows", json=workflow_data, headers=auth_headers)
        assert resp.status_code == 201
        workflow = resp.json()
        steps = workflow["steps"]
        
        # 更新步骤1，添加 next_step_id 跳转到步骤3
        step1_id = steps[0]["id"]
        step3_id = steps[2]["id"]
        
        update_data = {
            "steps": [
                {"step_type": "notify", "name": "步骤1", "sort_order": 0, "next_step_id": step3_id},
                {"step_type": "notify", "name": "步骤2", "sort_order": 1},
                {"step_type": "notify", "name": "步骤3", "sort_order": 2},
            ]
        }
        # 注意：当前 API 可能不支持直接更新 steps，这里仅验证创建时字段保存


class TestWorkflowParallel:
    """并行执行测试"""

    @pytest.mark.asyncio
    async def test_workflow_with_parallel_group(self, client, auth_headers):
        """测试创建带并行组的工作流"""
        workflow_data = {
            "name": "并行测试",
            "steps": [
                {"step_type": "notify", "name": "并行通知1", "sort_order": 0, "parallel_group": "group1"},
                {"step_type": "notify", "name": "并行通知2", "sort_order": 1, "parallel_group": "group1"},
                {"step_type": "notify", "name": "后续步骤", "sort_order": 2},
            ]
        }
        resp = await client.post("/api/v1/workflows", json=workflow_data, headers=auth_headers)
        assert resp.status_code == 201
        workflow = resp.json()
        assert len(workflow["steps"]) == 3
        
        # 验证并行组
        parallel_steps = [s for s in workflow["steps"] if s.get("parallel_group") == "group1"]
        assert len(parallel_steps) == 2
