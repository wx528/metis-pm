"""工作流超时检测

检查 WorkflowRun 是否超过步骤超时时间，超时则标记为 failed 并通知 admin。
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.core.notification import create_notification
from src.models.workflow import WorkflowRun, WorkflowRunStatus, WorkflowStep
from src.models.notification import NotificationType

logger = logging.getLogger(__name__)


async def check_workflow_run_timeouts():
    """检查所有运行中的 WorkflowRun 是否超时"""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        
        # 获取所有 running 或 waiting_approval 的 run
        result = await db.execute(
            select(WorkflowRun).where(
                WorkflowRun.status.in_([
                    WorkflowRunStatus.RUNNING,
                    WorkflowRunStatus.WAITING_APPROVAL,
                ])
            )
        )
        runs = result.scalars().all()
        
        timed_out_count = 0
        for run in runs:
            # 获取当前步骤的超时设置
            step_result = await db.execute(
                select(WorkflowStep).where(
                    WorkflowStep.workflow_id == run.workflow_id,
                    WorkflowStep.sort_order == run.current_step_index,
                )
            )
            step = step_result.scalar_one_or_none()
            
            if not step:
                continue
            
            # 计算已运行时间（处理 timezone naive/aware）
            started_at = run.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed = (now - started_at).total_seconds()
            timeout = step.timeout_seconds or 300  # 默认 5 分钟
            
            if elapsed > timeout:
                # 超时！标记为 failed
                run.status = WorkflowRunStatus.FAILED
                run.completed_at = now
                run.error_message = f"Step '{step.name}' timed out after {elapsed:.0f}s (limit: {timeout}s)"
                await db.commit()
                
                # 发送通知
                await create_notification(
                    db,
                    recipient="admin",
                    type=NotificationType.TASK_FAILED,
                    title=f"⚠️ WorkflowRun #{run.id} 超时",
                    body=run.error_message,
                    entity_type="workflow_run",
                    entity_id=run.id,
                )
                
                timed_out_count += 1
                logger.warning(f"WorkflowRun #{run.id} timed out: {run.error_message}")
        
        if timed_out_count > 0:
            logger.info(f"Workflow timeout check: {timed_out_count} runs timed out")


async def workflow_timeout_monitor():
    """后台任务：每 5 分钟检查一次工作流超时"""
    while True:
        try:
            await asyncio.sleep(300)  # 5 分钟检查一次
            await check_workflow_run_timeouts()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Workflow timeout check failed: {e}")
            await asyncio.sleep(300)
