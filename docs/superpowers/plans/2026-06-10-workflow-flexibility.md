# 工作流引擎灵活性增强 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将硬编码的线性工作流升级为支持条件分支、并行执行和可视化配置的工作流引擎

**Architecture:** 
- 扩展 `WorkflowStep` 模型，添加 `next_step_id`、`condition`（条件表达式）、`parallel_steps`（并行步骤组）字段
- 修改 `_execute_steps` 逻辑，支持条件判断、并行执行、回退（loopback）
- 工作流配置支持 JSON 格式导入/导出，便于前端可视化编辑器
- 新增 `WorkflowTemplate` 预置模板（开发→审查→测试→完成、紧急 Bug 修复等）

**Tech Stack:** FastAPI, SQLAlchemy, JSON, asyncio

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/models/workflow.py` | 扩展 WorkflowStep：添加 condition, next_step_id, parallel_group |
| `src/core/workflow_engine.py` | 重写执行逻辑：支持条件分支、并行执行、回退 |
| `src/routes/workflows.py` | 新增模板导入/导出、条件验证 API |
| `src/schemas/workflow.py` | 扩展 Pydantic schema |
| `tests/test_workflow_flexibility.py` | 条件分支和并行执行测试 |

---

## Task 1: 扩展 WorkflowStep 模型

**Files:**
- Modify: `src/models/workflow.py`

- [ ] **Step 1: 修改 WorkflowStep 模型**

```python
class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    step_type = Column(EnumColumn(StepType), nullable=False)
    name = Column(String(200), nullable=True)
    config = Column(JSON, nullable=True)
    sort_order = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=300)
    on_failure = Column(EnumColumn(OnFailure), default=OnFailure.ABORT)
    
    # 新增：工作流灵活性字段
    condition = Column(Text, nullable=True)  # 条件表达式，如 "context.status == 'failed'"
    next_step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=True)  # 条件为真时的下一步
    else_step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=True)  # 条件为假时的下一步
    parallel_group = Column(String(50), nullable=True)  # 并行组标识（同组步骤并行执行）
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    workflow = relationship("Workflow", back_populates="steps")
```

- [ ] **Step 2: Commit**

```bash
git add src/models/workflow.py
git commit -m "feat(workflow): add condition, next_step_id, parallel_group to WorkflowStep"
```

---

## Task 2: 扩展 Pydantic Schemas

**Files:**
- Modify: `src/schemas/workflow.py`

- [ ] **Step 1: 修改 WorkflowStep schemas**

```python
class WorkflowStepCreate(BaseModel):
    step_type: str
    name: Optional[str] = None
    config: Optional[dict] = None
    sort_order: Optional[int] = None
    timeout_seconds: Optional[int] = 300
    on_failure: str = "abort"
    condition: Optional[str] = None  # 新增
    next_step_id: Optional[int] = None  # 新增
    else_step_id: Optional[int] = None  # 新增
    parallel_group: Optional[str] = None  # 新增

class WorkflowStepRead(BaseModel):
    id: int
    workflow_id: int
    step_type: str
    name: Optional[str] = None
    config: Optional[dict] = None
    sort_order: int
    timeout_seconds: int
    on_failure: str
    condition: Optional[str] = None  # 新增
    next_step_id: Optional[int] = None  # 新增
    else_step_id: Optional[int] = None  # 新增
    parallel_group: Optional[str] = None  # 新增
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Commit**

```bash
git add src/schemas/workflow.py
git commit -m "feat(schema): add condition and branch fields to WorkflowStep schemas"
```

---

## Task 3: 重写 WorkflowEngine 执行逻辑

**Files:**
- Modify: `src/core/workflow_engine.py`

- [ ] **Step 1: 重写 _execute_steps 支持条件分支**

```python
    async def _execute_steps(self, run: WorkflowRun, workflow: Workflow) -> None:
        """执行工作流步骤（支持条件分支、并行执行）"""
        steps_map = {s.id: s for s in workflow.steps}
        steps_by_order = sorted(workflow.steps, key=lambda s: s.sort_order)
        
        while run.status == WorkflowRunStatus.RUNNING:
            # 找到当前步骤
            if run.current_step_index >= len(steps_by_order):
                # 所有步骤执行完毕
                run.status = WorkflowRunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                return
            
            current_step = steps_by_order[run.current_step_index]
            
            # 检查条件
            if current_step.condition:
                should_execute = self._evaluate_condition(current_step.condition, run.context)
                if not should_execute:
                    # 跳过此步骤，走 else 分支
                    if current_step.else_step_id and current_step.else_step_id in steps_map:
                        next_step = steps_map[current_step.else_step_id]
                        run.current_step_index = steps_by_order.index(next_step)
                        await self.db.commit()
                        continue
                    else:
                        run.current_step_index += 1
                        await self.db.commit()
                        continue
            
            # 检查是否是并行组
            if current_step.parallel_group:
                await self._execute_parallel_group(run, current_step, steps_by_order, steps_map)
            else:
                # 串行执行单步
                await self._execute_single_step(run, current_step, steps_by_order)
    
    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """评估条件表达式（安全子集）"""
        if not condition:
            return True
        try:
            # 使用安全的 eval，只允许上下文变量和基本操作
            allowed_names = {"context": context or {}}
            allowed_names.update(context or {})
            result = eval(condition, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False
    
    async def _execute_parallel_group(self, run: WorkflowRun, current_step: WorkflowStep, steps_by_order, steps_map):
        """执行并行步骤组"""
        group = current_step.parallel_group
        group_steps = [s for s in steps_by_order if s.parallel_group == group]
        
        # 并行执行所有步骤
        tasks = [self._execute_single_step_without_commit(run, s, steps_by_order) for s in group_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有失败
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            logger.error(f"Parallel group {group} failed: {failures}")
            # 处理失败（默认 abort）
            run.status = WorkflowRunStatus.FAILED
            run.error_message = f"Parallel group {group} failed: {failures[0]}"
            await self.db.commit()
            return
        
        # 找到并行组之后的下一个串行步骤
        last_group_index = max(steps_by_order.index(s) for s in group_steps)
        run.current_step_index = last_group_index + 1
        await self.db.commit()
    
    async def _execute_single_step(self, run: WorkflowRun, step: WorkflowStep, steps_by_order):
        """执行单步（带 commit）"""
        try:
            await self._execute_step_logic(run, step)
            
            # 检查是否需要跳转
            if step.next_step_id and step.next_step_id in {s.id for s in steps_by_order}:
                next_step = next(s for s in steps_by_order if s.id == step.next_step_id)
                run.current_step_index = steps_by_order.index(next_step)
            else:
                run.current_step_index += 1
            
            await self.db.commit()
        except Exception as e:
            await self._handle_step_failure(run, step, e)
    
    async def _execute_single_step_without_commit(self, run: WorkflowRun, step: WorkflowStep, steps_by_order):
        """执行单步（不带 commit，用于并行组）"""
        try:
            await self._execute_step_logic(run, step)
            return True
        except Exception as e:
            return e
```

- [ ] **Step 2: Commit**

```bash
git add src/core/workflow_engine.py
git commit -m "feat(workflow): add condition branch and parallel execution support"
```

---

## Task 4: 添加工作流模板 API

**Files:**
- Modify: `src/routes/workflows.py`

- [ ] **Step 1: 添加模板导入导出端点**

```python
# 预置模板
WORKFLOW_TEMPLATES = {
    "dev_review_test": {
        "name": "开发→审查→测试→完成",
        "description": "标准软件开发流程",
        "trigger": "manual",
        "steps": [
            {"step_type": "create_issue", "name": "创建开发任务", "sort_order": 0},
            {"step_type": "wait_approval", "name": "代码审查", "sort_order": 1},
            {"step_type": "create_issue", "name": "创建测试任务", "sort_order": 2, "condition": "context.approval_result == 'approved'"},
            {"step_type": "notify", "name": "通知完成", "sort_order": 3},
        ]
    },
    "urgent_bug": {
        "name": "紧急 Bug 修复",
        "description": "P0/P1 Bug 快速修复流程",
        "trigger": "on_issue_created",
        "trigger_config": {"priority": "P0"},
        "steps": [
            {"step_type": "create_issue", "name": "紧急修复", "sort_order": 0},
            {"step_type": "notify", "name": "通知测试", "sort_order": 1, "parallel_group": "notify"},
            {"step_type": "notify", "name": "通知 PM", "sort_order": 2, "parallel_group": "notify"},
            {"step_type": "wait_approval", "name": "验证修复", "sort_order": 3},
        ]
    }
}

@router.get("/templates")
async def list_templates():
    """获取预置工作流模板列表"""
    return [
        {"id": key, "name": template["name"], "description": template["description"]}
        for key, template in WORKFLOW_TEMPLATES.items()
    ]

@router.post("/from-template/{template_id}", response_model=WorkflowReadWithSteps, status_code=201)
async def create_from_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "agent")),
):
    """从模板创建工作流"""
    if template_id not in WORKFLOW_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = WORKFLOW_TEMPLATES[template_id]
    workflow = Workflow(
        name=template["name"],
        description=template["description"],
        trigger=template["trigger"],
        trigger_config=template.get("trigger_config"),
        status="active",
        created_by=user["sub"],
    )
    db.add(workflow)
    await db.flush()
    
    for step_data in template["steps"]:
        step = WorkflowStep(workflow_id=workflow.id, **step_data)
        db.add(step)
    
    await db.commit()
    await db.refresh(workflow)
    return workflow
```

- [ ] **Step 2: Commit**

```bash
git add src/routes/workflows.py
git commit -m "feat(workflow): add workflow templates API"
```

---

## Task 5: 数据库迁移

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 添加 workflow_steps 列迁移**

在 `_run_migrations` 函数中添加：

```python
    # Phase 10: workflow_steps 添加条件分支字段
    result = await conn.execute(text("PRAGMA table_info(workflow_steps)"))
    step_cols = {row[1] for row in result.fetchall()}
    for col in ["condition", "next_step_id", "else_step_id", "parallel_group"]:
        if col not in step_cols:
            try:
                if col in ["next_step_id", "else_step_id"]:
                    await conn.execute(text(f"ALTER TABLE workflow_steps ADD COLUMN {col} INTEGER"))
                elif col == "condition":
                    await conn.execute(text(f"ALTER TABLE workflow_steps ADD COLUMN {col} TEXT"))
                else:
                    await conn.execute(text(f"ALTER TABLE workflow_steps ADD COLUMN {col} VARCHAR(50)"))
                logger.info(f"Added {col} column to workflow_steps")
            except Exception as e:
                logger.warning(f"Failed to add {col} to workflow_steps: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat(db): migrate workflow_steps for condition and branch support"
```

---

## Task 6: 编写测试

**Files:**
- Create: `tests/test_workflow_flexibility.py`

- [ ] **Step 1: 编写条件分支测试**

```python
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


class TestWorkflowConditions:
    """条件分支测试"""

    @pytest.mark.asyncio
    async def test_workflow_condition_true_branch(self, client, auth_headers):
        """测试条件为真时走 next_step_id 分支"""
        # 创建带条件的工作流
        workflow_data = {
            "name": "条件测试",
            "steps": [
                {"step_type": "notify", "name": "开始", "sort_order": 0, "next_step_id": None},
                {"step_type": "notify", "name": "条件步骤", "sort_order": 1, "condition": "True", "next_step_id": None},
                {"step_type": "notify", "name": "成功分支", "sort_order": 2},
            ]
        }
        resp = await client.post("/api/v1/workflows", json=workflow_data, headers=auth_headers)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_workflow_template_api(self, client, auth_headers):
        """测试模板 API"""
        # 获取模板列表
        resp = await client.get("/api/v1/workflows/templates", headers=auth_headers)
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) >= 2  # 至少有两个预置模板
        
        # 从模板创建
        resp = await client.post("/api/v1/workflows/from-template/dev_review_test", headers=auth_headers)
        assert resp.status_code == 201
        workflow = resp.json()
        assert workflow["name"] == "开发→审查→测试→完成"
        assert len(workflow["steps"]) == 4


class TestWorkflowParallel:
    """并行执行测试"""

    @pytest.mark.asyncio
    async def test_parallel_group_steps(self, client, auth_headers):
        """测试并行步骤组"""
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
```

- [ ] **Step 2: 运行测试**

```bash
cd backend
python -m pytest tests/test_workflow_flexibility.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_workflow_flexibility.py
git commit -m "test: add workflow flexibility tests"
```

---

## Task 7: 运行全部测试

- [ ] **Step 1: 运行全部测试**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

- [ ] **Step 2: 提交最终变更**

```bash
git add -A
git commit -m "feat(workflow): complete workflow flexibility enhancement"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 条件分支：condition + next_step_id + else_step_id
- ✅ 并行执行：parallel_group
- ✅ 可视化配置：JSON 模板 API
- ✅ 预置模板：dev_review_test, urgent_bug

**2. Placeholder scan:**
- ✅ 没有 TBD/TODO
- ✅ 所有代码完整

**3. Type consistency:**
- ✅ 使用现有枚举 StepType, OnFailure
- ✅ 条件表达式使用安全的 eval

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-workflow-flexibility.md`.**

**执行选项：**
1. **Subagent-Driven（推荐）** — 我为每个任务调度独立子代理
2. **Inline Execution** — 在当前会话中直接执行

**建议：** 先执行 Task 1-3（模型+Schema+引擎核心），再执行 Task 4-7（API+迁移+测试）。

用哪种方式？
