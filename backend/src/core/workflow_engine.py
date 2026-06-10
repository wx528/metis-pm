"""Phase 6 — 工作流引擎核心"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.workflow import (
    Workflow, WorkflowStep, WorkflowRun,
    WorkflowStatus, WorkflowRunStatus, StepType, OnFailure,
)
from src.models.notification import NotificationType
from src.core.notification import create_notification

logger = logging.getLogger(__name__)

# RETRY 策略配置
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2  # 指数退避基础延迟


class WorkflowEngine:
    """轻量级工作流引擎：trigger → execute_steps → wait_approval → resume"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger(
        self,
        workflow: Workflow,
        triggered_by: str = "system",
        initial_context: Optional[dict] = None,
    ) -> WorkflowRun:
        """触发工作流，创建 Run 并开始执行"""
        run = WorkflowRun(
            workflow_id=workflow.id,
            triggered_by=triggered_by,
            status=WorkflowRunStatus.RUNNING,
            current_step_index=0,
            context=initial_context or {},
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        # 异步执行步骤（简化版：同步执行到 wait 或完成）
        await self._execute_steps(run, workflow)
        return run

    async def resume(self, run: WorkflowRun, approved: bool = True, approved_by: str = "admin") -> WorkflowRun:
        """恢复暂停的工作流（审批后继续）"""
        if not approved:
            run.status = WorkflowRunStatus.ABORTED
            run.completed_at = datetime.now(timezone.utc)
            run.context = run.context or {}
            run.context["approval_result"] = "rejected"
            run.context["approved_by"] = approved_by
            await self.db.commit()
            await self.db.refresh(run)

            # 通知触发者
            await create_notification(
                self.db,
                recipient=run.triggered_by or "admin",
                type=NotificationType.INFO,
                title=f"工作流执行已被拒绝",
                body=f"WorkflowRun #{run.id} 被 {approved_by} 拒绝",
                entity_type="workflow_run",
                entity_id=run.id,
                created_by=approved_by,
            )
            return run

        # 审批通过，继续执行
        run.context = run.context or {}
        run.context["approval_result"] = "approved"
        run.context["approved_by"] = approved_by
        run.current_step_index += 1  # 跳过 wait_approval 步骤
        run.status = WorkflowRunStatus.RUNNING
        await self.db.commit()
        await self.db.refresh(run)

        # 重新加载 workflow 和 steps
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == run.workflow_id).options(selectinload(Workflow.steps))
        )
        workflow = result.scalar_one()
        await self._execute_steps(run, workflow)
        return run

    async def _execute_steps(self, run: WorkflowRun, workflow: Workflow) -> None:
        """执行工作流步骤（支持条件分支、并行执行）"""
        steps = sorted(workflow.steps, key=lambda s: s.sort_order)
        steps_map = {s.id: s for s in steps}

        while run.status == WorkflowRunStatus.RUNNING:
            if run.current_step_index >= len(steps):
                # 所有步骤执行完毕
                run.status = WorkflowRunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                return

            current_step = steps[run.current_step_index]

            # 检查条件
            if current_step.condition:
                should_execute = self._evaluate_condition(current_step.condition, run.context)
                if not should_execute:
                    # 跳过此步骤，走 else 分支
                    if current_step.else_step_id and current_step.else_step_id in steps_map:
                        next_step = steps_map[current_step.else_step_id]
                        run.current_step_index = steps.index(next_step)
                        await self.db.commit()
                        continue
                    else:
                        run.current_step_index += 1
                        await self.db.commit()
                        continue

            # 检查是否是并行组
            if current_step.parallel_group:
                await self._execute_parallel_group(run, current_step, steps, steps_map, workflow)
            else:
                # 串行执行单步
                await self._execute_single_step(run, current_step, steps, workflow)

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

    async def _execute_parallel_group(self, run: WorkflowRun, current_step: WorkflowStep, steps, steps_map, workflow: Workflow):
        """执行并行步骤组"""
        group = current_step.parallel_group
        group_steps = [s for s in steps if s.parallel_group == group]

        # 并行执行所有步骤
        tasks = [self._execute_step_logic(s, run, workflow) for s in group_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查是否有失败
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            logger.error(f"Parallel group {group} failed: {failures}")
            run.status = WorkflowRunStatus.FAILED
            run.error_message = f"Parallel group {group} failed: {failures[0]}"
            await self.db.commit()
            return

        # 找到并行组之后的下一个串行步骤
        last_group_index = max(steps.index(s) for s in group_steps)
        run.current_step_index = last_group_index + 1
        await self.db.commit()

    async def _execute_single_step(self, run: WorkflowRun, step: WorkflowStep, steps, workflow: Workflow):
        """执行单步"""
        try:
            result = await self._execute_step(step, run, workflow)

            if step.step_type == StepType.WAIT_APPROVAL:
                run.status = WorkflowRunStatus.WAITING_APPROVAL
                await self.db.commit()
                await self.db.refresh(run)
                return

            # 将步骤结果存入上下文
            run.context = run.context or {}
            run.context[f"step_{step.id}_result"] = result

            # 检查是否需要跳转
            if step.next_step_id and step.next_step_id in {s.id for s in steps}:
                next_step = next(s for s in steps if s.id == step.next_step_id)
                run.current_step_index = steps.index(next_step)
            else:
                run.current_step_index += 1

            await self.db.commit()

        except Exception as e:
            await self._handle_step_failure(run, step, e, workflow)

    async def _execute_step_logic(self, step: WorkflowStep, run: WorkflowRun, workflow: Workflow):
        """执行步骤逻辑（不带状态管理，用于并行组）"""
        return await self._execute_step(step, run, workflow)

    async def _handle_step_failure(self, run: WorkflowRun, step: WorkflowStep, e: Exception, workflow: Workflow):
        """处理步骤失败"""
        logger.error(f"Workflow step {step.id} failed: {e}")
        run.error_message = str(e)

        if step.on_failure == OnFailure.ABORT:
            run.status = WorkflowRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return
        elif step.on_failure == OnFailure.SKIP:
            run.current_step_index += 1
            await self.db.commit()
        elif step.on_failure == OnFailure.NOTIFY_HUMAN:
            await create_notification(
                self.db,
                recipient="admin",
                type=NotificationType.WORKFLOW_PAUSED,
                title=f"工作流步骤执行失败: {step.name or step.step_type}",
                body=f"WorkflowRun #{run.id} 步骤失败: {e}",
                entity_type="workflow_run",
                entity_id=run.id,
                created_by="system",
                project_id=workflow.project_id,
            )
            run.status = WorkflowRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return
        else:
            # RETRY
            retry_count = (run.context or {}).get(f"step_{step.id}_retries", 0) + 1
            if retry_count <= MAX_RETRIES:
                delay = RETRY_BASE_DELAY_SECONDS * (2 ** (retry_count - 1))
                logger.warning(
                    f"Workflow step {step.id} failed (attempt {retry_count}/{MAX_RETRIES}), "
                    f"retrying in {delay}s: {e}"
                )
                run.context = run.context or {}
                run.context[f"step_{step.id}_retries"] = retry_count
                await self.db.commit()
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Workflow step {step.id} failed after {MAX_RETRIES} retries: {e}"
                )
                run.status = WorkflowRunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                return

    async def _execute_step(self, step: WorkflowStep, run: WorkflowRun, workflow: Workflow) -> dict:
        """执行单个步骤"""
        config = step.config or {}
        ctx = run.context or {}

        if step.step_type == StepType.CREATE_ISSUE:
            from src.models.issue import Issue, IssueType, IssuePriority, IssueSource
            issue = Issue(
                title=config.get("title", f"Workflow auto-created issue"),
                description=config.get("description", f"Created by workflow #{workflow.id}"),
                issue_type=config.get("issue_type", "task"),
                priority=config.get("priority", "P2"),
                source=IssueSource.AI_AGENT,
                project_id=workflow.project_id,
                milestone_id=config.get("milestone_id"),
            )
            self.db.add(issue)
            await self.db.flush()
            return {"issue_id": issue.id, "issue_title": issue.title}

        elif step.step_type == StepType.UPDATE_ISSUE:
            from src.models.issue import Issue, IssueStatus
            issue_id = config.get("issue_id") or ctx.get("issue_id")
            if not issue_id:
                raise ValueError("No issue_id in config or context")
            result = await self.db.execute(select(Issue).where(Issue.id == issue_id))
            issue = result.scalar_one_or_none()
            if not issue:
                raise ValueError(f"Issue #{issue_id} not found")
            if "status" in config:
                issue.status = config["status"]
            if "priority" in config:
                issue.priority = config["priority"]
            await self.db.flush()
            return {"issue_id": issue.id, "updated_fields": list(config.keys())}

        elif step.step_type == StepType.NOTIFY:
            await create_notification(
                self.db,
                recipient=config.get("recipient", "admin"),
                type=NotificationType.INFO,
                title=config.get("title", "工作流通知"),
                body=config.get("body", ""),
                entity_type=config.get("entity_type"),
                entity_id=config.get("entity_id"),
                created_by="workflow",
                project_id=workflow.project_id,
            )
            return {"notified": config.get("recipient", "admin")}

        elif step.step_type == StepType.WAIT_APPROVAL:
            # 通知 admin 审批
            await create_notification(
                self.db,
                recipient="admin",
                type=NotificationType.APPROVAL_NEEDED,
                title=config.get("title", f"工作流等待审批: {workflow.name}"),
                body=config.get("body", f"WorkflowRun #{run.id} 等待您的审批"),
                entity_type="workflow_run",
                entity_id=run.id,
                created_by=run.triggered_by or "system",
                project_id=workflow.project_id,
            )
            return {"waiting": True}

        elif step.step_type == StepType.PROPOSE_PLAN:
            from src.models.plan import Plan, PlanStatus, PlanSource
            plan = Plan(
                title=config.get("title", f"Workflow proposed plan"),
                description=config.get("description", f"Proposed by workflow #{workflow.id}"),
                status=PlanStatus.PENDING_APPROVAL,
                proposed_by=PlanSource.AI_AGENT,
                project_id=workflow.project_id,
            )
            self.db.add(plan)
            await self.db.flush()
            return {"plan_id": plan.id, "plan_title": plan.title}

        else:
            raise ValueError(f"Unknown step type: {step.step_type}")


async def check_and_trigger_workflows(
    db: AsyncSession,
    trigger_type: str,
    project_id: Optional[int],
    context: Optional[dict] = None,
) -> list[WorkflowRun]:
    """检查是否有匹配的工作流需要触发"""
    result = await db.execute(
        select(Workflow)
        .where(
            Workflow.trigger == trigger_type,
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.project_id == project_id if project_id else True,
        )
        .options(selectinload(Workflow.steps))
    )
    workflows = result.scalars().all()

    runs = []
    engine = WorkflowEngine(db)

    for workflow in workflows:
        # 检查 trigger_config 过滤条件
        if workflow.trigger_config and context:
            match = True
            for key, value in workflow.trigger_config.items():
                if context.get(key) != value:
                    match = False
                    break
            if not match:
                continue

        try:
            run = await engine.trigger(workflow, triggered_by="auto_trigger", initial_context=context)
            runs.append(run)
            logger.info(f"Triggered workflow #{workflow.id} '{workflow.name}' (run #{run.id})")
        except Exception as e:
            logger.error(f"Failed to trigger workflow #{workflow.id}: {e}")

    return runs
