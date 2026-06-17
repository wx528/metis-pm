"""Phase 6 — 工作流引擎核心（步骤级持久化）

每步执行前后实时写入 WorkflowStepRun 状态到数据库。
backend 重启后，通过 _recover_workflow_runs 自动从最后成功步骤恢复。
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.workflow import (
    Workflow, WorkflowStep, WorkflowRun, WorkflowStepRun,
    WorkflowStatus, WorkflowRunStatus, StepRunStatus, StepType, OnFailure,
)
from src.models.notification import NotificationType
from src.core.notification import create_notification
from src.core.metrics import workflow_step_duration_seconds, workflow_step_total

logger = logging.getLogger(__name__)

# RETRY 策略配置
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2  # 指数退避基础延迟


class WorkflowEngine:
    """轻量级工作流引擎：trigger → execute_steps → wait_approval → resume

    步骤级持久化：每步执行前创建 WorkflowStepRun(pending)，
    执行中更新为 running，完成后更新为 completed/failed/skipped。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── 步骤级状态管理 ─────────────────────────────────

    async def _get_or_create_step_run(
        self, run: WorkflowRun, step: WorkflowStep,
    ) -> WorkflowStepRun:
        """获取已有 step_run 或创建新的"""
        result = await self.db.execute(
            select(WorkflowStepRun).where(
                WorkflowStepRun.run_id == run.id,
                WorkflowStepRun.step_id == step.id,
            )
        )
        step_run = result.scalar_one_or_none()
        if step_run:
            return step_run

        step_run = WorkflowStepRun(
            run_id=run.id,
            step_id=step.id,
            status=StepRunStatus.PENDING,
        )
        self.db.add(step_run)
        await self.db.flush()
        return step_run

    async def _mark_step(self, step_run: WorkflowStepRun, status: StepRunStatus,
                         result: dict = None, error: str = None):
        """更新步骤执行状态并立即提交"""
        step_run.status = status
        if result is not None:
            step_run.result = result
        if error is not None:
            step_run.error = error
        if status == StepRunStatus.RUNNING:
            step_run.started_at = datetime.now(timezone.utc)
        if status in (StepRunStatus.COMPLETED, StepRunStatus.FAILED, StepRunStatus.SKIPPED):
            step_run.completed_at = datetime.now(timezone.utc)
            # 记录步骤耗时指标
            if step_run.started_at:
                duration = (step_run.completed_at - step_run.started_at).total_seconds()
                step_type = step_run.step.type.value if step_run.step else "unknown"
                workflow_step_duration_seconds.labels(
                    step_type=step_type, status=status.value
                ).observe(duration)
            workflow_step_total.labels(
                step_type=step_run.step.type.value if step_run.step else "unknown",
                status=status.value,
            ).inc()
        await self.db.commit()

    # ─── 触发与恢复 ─────────────────────────────────────

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

        # 为所有步骤创建 pending step_run
        steps = sorted(workflow.steps, key=lambda s: s.sort_order)
        for step in steps:
            step_run = WorkflowStepRun(
                run_id=run.id,
                step_id=step.id,
                status=StepRunStatus.PENDING,
            )
            self.db.add(step_run)
        await self.db.commit()

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

        # 标记 WAIT_APPROVAL 步骤的 step_run 为 COMPLETED
        steps_result = await self.db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == run.workflow_id)
            .order_by(WorkflowStep.sort_order)
        )
        steps = steps_result.scalars().all()
        if 0 <= run.current_step_index < len(steps):
            approval_step = steps[run.current_step_index]
            if approval_step.step_type == StepType.WAIT_APPROVAL:
                sr_result = await self.db.execute(
                    select(WorkflowStepRun).where(
                        WorkflowStepRun.run_id == run.id,
                        WorkflowStepRun.step_id == approval_step.id,
                    )
                )
                approval_sr = sr_result.scalar_one_or_none()
                if approval_sr:
                    await self._mark_step(approval_sr, StepRunStatus.COMPLETED,
                                          result={"approval_result": "approved", "approved_by": approved_by})

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

    # ─── 步骤执行 ───────────────────────────────────────

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
            step_run = await self._get_or_create_step_run(run, current_step)

            # 已完成的步骤直接跳过（断点续传）
            if step_run.status == StepRunStatus.COMPLETED:
                # 将结果写入 context
                if step_run.result:
                    run.context = run.context or {}
                    run.context[f"step_{current_step.id}_result"] = step_run.result
                run.current_step_index += 1
                await self.db.commit()
                continue

            # 已跳过的步骤也跳过
            if step_run.status == StepRunStatus.SKIPPED:
                run.current_step_index += 1
                await self.db.commit()
                continue

            # 检查条件
            if current_step.condition:
                should_execute = self._evaluate_condition(current_step.condition, run.context)
                if not should_execute:
                    await self._mark_step(step_run, StepRunStatus.SKIPPED)
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
                await self._execute_single_step(run, current_step, step_run, steps, workflow)

    # ─── 条件评估 ────────────────────────────────────────

    # 支持的安全操作符
    _SAFE_OPS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
    }

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """评估条件表达式（安全子集，不使用 eval）"""
        if not condition:
            return True
        try:
            ctx = context or {}
            if " or " in condition.lower():
                parts = self._split_logical(condition, "or")
                return any(self._evaluate_condition(p.strip(), ctx) for p in parts)
            if " and " in condition.lower():
                parts = self._split_logical(condition, "and")
                return all(self._evaluate_condition(p.strip(), ctx) for p in parts)

            cond = condition.strip()
            if cond.lower().startswith("not "):
                return not self._evaluate_condition(cond[4:].strip(), ctx)

            for op_str, op_fn in self._SAFE_OPS.items():
                parts = cond.split(f" {op_str} ", 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), ctx)
                    right = self._resolve_value(parts[1].strip(), ctx)
                    return bool(op_fn(left, right))

            val = self._resolve_value(cond, ctx)
            return bool(val)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False

    @staticmethod
    def _split_logical(expr: str, op: str) -> list[str]:
        parts = []
        current = []
        i = 0
        op_pattern = f" {op} "
        while i < len(expr):
            if expr[i:i + len(op_pattern)].lower() == op_pattern:
                parts.append("".join(current))
                current = []
                i += len(op_pattern)
            else:
                current.append(expr[i])
                i += 1
        parts.append("".join(current))
        return parts

    @staticmethod
    def _resolve_value(token: str, context: dict):
        if not token:
            return None
        if (token.startswith('"') and token.endswith('"')) or \
           (token.startswith("'") and token.endswith("'")):
            return token[1:-1]
        if token in context:
            return context[token]
        if "." in token:
            parts = token.split(".", 1)
            if parts[0] in context:
                val = context[parts[0]]
                if isinstance(val, dict):
                    return val.get(parts[1])
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        return token

    # ─── 并行执行 ────────────────────────────────────────

    async def _execute_parallel_group(self, run: WorkflowRun, current_step: WorkflowStep, steps, steps_map, workflow: Workflow):
        """执行并行步骤组"""
        group = current_step.parallel_group
        group_steps = [s for s in steps if s.parallel_group == group]

        # 标记所有步骤为 running
        step_runs = []
        for s in group_steps:
            sr = await self._get_or_create_step_run(run, s)
            if sr.status not in (StepRunStatus.COMPLETED, StepRunStatus.SKIPPED):
                await self._mark_step(sr, StepRunStatus.RUNNING)
            step_runs.append(sr)

        # 并行执行所有步骤
        tasks = [self._execute_step_logic(s, run, workflow) for s in group_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        failures = []
        for s, sr, r in zip(group_steps, step_runs, results):
            if isinstance(r, Exception):
                await self._mark_step(sr, StepRunStatus.FAILED, error=str(r))
                failures.append(r)
            else:
                await self._mark_step(sr, StepRunStatus.COMPLETED, result=r)
                run.context = run.context or {}
                run.context[f"step_{s.id}_result"] = r

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

    # ─── 串行执行 ────────────────────────────────────────

    async def _execute_single_step(self, run: WorkflowRun, step: WorkflowStep, step_run: WorkflowStepRun, steps, workflow: Workflow):
        """执行单步（带超时控制 + 步骤级持久化 + 循环重试）

        统一状态管理：不在 except 中提前标记 FAILED，
        由 _handle_step_failure 统一决定最终状态（SKIP/RETRY/ABORT）。
        """
        # 标记为 running
        await self._mark_step(step_run, StepRunStatus.RUNNING)

        timeout = step.timeout_seconds or 300

        try:
            result = await asyncio.wait_for(
                self._execute_step(step, run, workflow),
                timeout=timeout,
            )

            if step.step_type == StepType.WAIT_APPROVAL:
                # WAIT_APPROVAL 不标记完成，等待 resume
                run.status = WorkflowRunStatus.WAITING_APPROVAL
                await self.db.commit()
                await self.db.refresh(run)
                return

            # 标记步骤完成
            await self._mark_step(step_run, StepRunStatus.COMPLETED, result=result)

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

        except (asyncio.TimeoutError, Exception) as e:
            error_msg = f"Step timed out after {timeout}s" if isinstance(e, asyncio.TimeoutError) else str(e)
            logger.error(f"Workflow step {step.id} failed: {error_msg}")
            # 不提前标记 FAILED，交给 _handle_step_failure 统一处理
            await self._handle_step_failure(run, step, step_run, error_msg, steps, workflow)

    async def _execute_step_logic(self, step: WorkflowStep, run: WorkflowRun, workflow: Workflow):
        """执行步骤逻辑（不带状态管理，用于并行组，带超时）"""
        timeout = step.timeout_seconds or 300
        return await asyncio.wait_for(
            self._execute_step(step, run, workflow),
            timeout=timeout,
        )

    # ─── 失败处理 ────────────────────────────────────────

    async def _handle_step_failure(
        self, run: WorkflowRun, step: WorkflowStep, step_run: WorkflowStepRun,
        error_msg: str, steps, workflow: Workflow,
    ):
        """处理步骤失败 — 统一决定 step_run 最终状态，避免双重标记"""
        run.error_message = error_msg

        if step.on_failure == OnFailure.ABORT:
            await self._mark_step(step_run, StepRunStatus.FAILED, error=error_msg)
            run.status = WorkflowRunStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return

        elif step.on_failure == OnFailure.SKIP:
            # 直接标记 SKIPPED（不经过 FAILED 中间态）
            await self._mark_step(step_run, StepRunStatus.SKIPPED, error=error_msg)
            run.current_step_index += 1
            await self.db.commit()
            return

        elif step.on_failure == OnFailure.NOTIFY_HUMAN:
            await self._mark_step(step_run, StepRunStatus.FAILED, error=error_msg)
            await create_notification(
                self.db,
                recipient="admin",
                type=NotificationType.WORKFLOW_PAUSED,
                title=f"工作流步骤执行失败: {step.name or step.step_type}",
                body=f"WorkflowRun #{run.id} 步骤失败: {error_msg}",
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
            # RETRY — 循环重试，不递归
            while True:
                step_run.retry_count += 1
                retry_count = step_run.retry_count

                if retry_count > MAX_RETRIES:
                    logger.error(
                        f"Workflow step {step.id} failed after {MAX_RETRIES} retries: {error_msg}"
                    )
                    await self._mark_step(step_run, StepRunStatus.FAILED, error=error_msg)
                    run.status = WorkflowRunStatus.FAILED
                    run.completed_at = datetime.now(timezone.utc)
                    await self.db.commit()
                    return

                delay = RETRY_BASE_DELAY_SECONDS * (2 ** (retry_count - 1))
                logger.warning(
                    f"Workflow step {step.id} failed (attempt {retry_count}/{MAX_RETRIES}), "
                    f"retrying in {delay}s: {error_msg}"
                )
                # 重置 step_run 为 pending 等待重试
                await self._mark_step(step_run, StepRunStatus.PENDING)
                await self.db.commit()
                await asyncio.sleep(delay)

                # 重新执行当前步骤
                await self._mark_step(step_run, StepRunStatus.RUNNING)
                timeout = step.timeout_seconds or 300
                try:
                    result = await asyncio.wait_for(
                        self._execute_step(step, run, workflow),
                        timeout=timeout,
                    )

                    if step.step_type == StepType.WAIT_APPROVAL:
                        run.status = WorkflowRunStatus.WAITING_APPROVAL
                        await self.db.commit()
                        return

                    # 重试成功
                    await self._mark_step(step_run, StepRunStatus.COMPLETED, result=result)
                    run.context = run.context or {}
                    run.context[f"step_{step.id}_result"] = result
                    if step.next_step_id and step.next_step_id in {s.id for s in steps}:
                        next_step = next(s for s in steps if s.id == step.next_step_id)
                        run.current_step_index = steps.index(next_step)
                    else:
                        run.current_step_index += 1
                    await self.db.commit()
                    return

                except (asyncio.TimeoutError, Exception) as retry_e:
                    error_msg = f"Step timed out after {timeout}s" if isinstance(retry_e, asyncio.TimeoutError) else str(retry_e)
                    logger.error(f"Workflow step {step.id} retry {retry_count} failed: {error_msg}")
                    # 继续循环，判断是否还有重试机会

    # ─── 步骤逻辑 ────────────────────────────────────────

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
            from src.models.plan import Plan, PlanStatus
            plan = Plan(
                title=config.get("title", f"Workflow proposed plan"),
                description=config.get("description", f"Proposed by workflow #{workflow.id}"),
                status=PlanStatus.PENDING,
                proposed_by="ai_agent",
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
