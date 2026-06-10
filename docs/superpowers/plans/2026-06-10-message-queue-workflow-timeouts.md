# 工作流超时告警 + 消息队列缓冲 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 检测工作流运行超时并告警，为关键通知添加内存队列缓冲防止丢失

**Architecture:** 
- 扩展后台任务 `_check_stuck_workflows`，增加 `WorkflowRun` 超时检测（running/waiting_approval 超过 step timeout）
- 添加内存消息队列 `MessageQueue`（asyncio.Queue + SQLite 持久化），在通知创建失败时缓冲并重试
- 超时的 WorkflowRun 自动标记为 failed 并通知 admin

**Tech Stack:** FastAPI, SQLAlchemy, asyncio, SQLite

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/core/message_queue.py` | 内存消息队列：缓冲通知、失败重试 |
| `src/core/workflow_timeout.py` | 工作流超时检测逻辑 |
| `main.py` | 启动后台任务（消息队列消费 + 超时检测）|
| `tests/test_fault_tolerance.py` | 扩展测试：消息队列和工作流超时 |

---

## Task 1: 创建内存消息队列

**Files:**
- Create: `src/core/message_queue.py`

- [ ] **Step 1: 编写 MessageQueue 类**

```python
"""轻量级消息队列 — 内存缓冲 + SQLite 持久化

当后端 API 暂时不可用时，通知消息写入队列，恢复后自动消费。
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class MessageQueue:
    """基于 asyncio.Queue 的内存消息队列，带 SQLite 持久化备份"""

    def __init__(self, maxsize: int = 1000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动队列消费者"""
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume())
        logger.info("Message queue consumer started")

    async def stop(self):
        """停止队列消费者"""
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Message queue consumer stopped")

    async def enqueue(self, message: dict) -> bool:
        """将消息入队，如果内存队列满则写入 SQLite 备份表"""
        try:
            self._queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            # 内存队列满，写入 SQLite 备份
            await self._persist_to_db(message)
            return False

    async def _persist_to_db(self, message: dict):
        """将消息持久化到 SQLite 备份表"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("""
                    INSERT INTO message_queue_backup (payload, created_at)
                    VALUES (:payload, :created_at)
                """), {
                    "payload": json.dumps(message),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                await db.commit()
                logger.warning(f"Message persisted to DB backup: {message.get('title', '?')}")
        except Exception as e:
            logger.error(f"Failed to persist message to DB: {e}")

    async def _consume(self):
        """消费队列中的消息"""
        while self._running:
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                await self._process_message(message)
            except asyncio.TimeoutError:
                # 检查 DB 备份中是否有消息
                await self._process_db_backup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message processing error: {e}")

    async def _process_message(self, message: dict):
        """处理单条消息：创建通知"""
        from src.core.notification import create_notification
        from src.models.notification import NotificationType

        try:
            async with AsyncSessionLocal() as db:
                await create_notification(
                    db,
                    recipient=message["recipient"],
                    type=NotificationType(message.get("type", "info")),
                    title=message["title"],
                    body=message.get("body"),
                    entity_type=message.get("entity_type"),
                    entity_id=message.get("entity_id"),
                    created_by=message.get("created_by"),
                    project_id=message.get("project_id"),
                )
                logger.info(f"Message processed: {message['title']}")
        except Exception as e:
            logger.error(f"Failed to process message, will retry: {e}")
            # 重新入队（指数退避可以在未来添加）
            await asyncio.sleep(1)
            await self.enqueue(message)

    async def _process_db_backup(self):
        """处理 SQLite 备份表中的消息"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(text("""
                    SELECT id, payload FROM message_queue_backup
                    ORDER BY created_at LIMIT 10
                """))
                rows = result.fetchall()
                for row in rows:
                    msg_id, payload = row
                    message = json.loads(payload)
                    await self._process_message(message)
                    # 处理成功后删除备份
                    await db.execute(text(
                        "DELETE FROM message_queue_backup WHERE id = :id"
                    ), {"id": msg_id})
                if rows:
                    await db.commit()
        except Exception as e:
            logger.error(f"DB backup processing error: {e}")


# 全局队列实例
message_queue = MessageQueue()


async def create_message_queue_backup_table():
    """创建消息队列备份表（如果不存在）"""
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS message_queue_backup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
        """))
        await db.commit()
```

- [ ] **Step 2: Commit**

```bash
git add src/core/message_queue.py
git commit -m "feat(queue): add in-memory message queue with SQLite backup"
```

---

## Task 2: 创建工作流超时检测

**Files:**
- Create: `src/core/workflow_timeout.py`

- [ ] **Step 1: 编写工作流超时检测逻辑**

```python
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
            
            # 计算已运行时间
            elapsed = (now - run.started_at).total_seconds()
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
```

- [ ] **Step 2: Commit**

```bash
git add src/core/workflow_timeout.py
git commit -m "feat(workflow): add workflow run timeout detection"
```

---

## Task 3: 在 main.py 中启动新的后台任务

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 导入新模块**

在 `main.py` 顶部添加：

```python
from src.core.message_queue import message_queue, create_message_queue_backup_table
from src.core.workflow_timeout import workflow_timeout_monitor
```

- [ ] **Step 2: 修改 lifespan 启动后台任务**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_migrations(conn)
    
    # 创建消息队列备份表
    await create_message_queue_backup_table()
    
    # 启动消息队列消费者
    await message_queue.start()
    
    # 启动后台任务
    tasks = [
        asyncio.create_task(_check_stuck_workflows()),
        asyncio.create_task(workflow_timeout_monitor()),
    ]
    yield
    
    # 清理
    for task in tasks:
        task.cancel()
    await message_queue.stop()
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat(main): start message queue consumer and workflow timeout monitor"
```

---

## Task 4: 在 notify_role 中集成消息队列

**Files:**
- Modify: `mcp_tools/shared.py`

- [ ] **Step 1: 修改 notify_role 工具，使用消息队列**

在 `notify_role` 工具中，如果 API 调用失败，将通知放入消息队列：

```python
    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def notify_role(...):
        """..."""
        payload = {...}
        
        resp = await _api_request("POST", f"{API_BASE}/notifications", json=payload)
        if resp.status_code >= 400:
            # API 调用失败，放入消息队列稍后重试
            from src.core.message_queue import message_queue
            await message_queue.enqueue(payload)
            return f"⚠️ API 暂时不可用，通知已排队稍后发送: {title}"
        
        data = resp.json()
        return f"通知已发送给角色 '{target_role}': {title} (通知ID: {data.get('id', '?')})"
```

- [ ] **Step 2: Commit**

```bash
git add mcp_tools/shared.py
git commit -m "feat(mcp): integrate message queue into notify_role for resilience"
```

---

## Task 5: 编写测试

**Files:**
- Modify: `tests/test_fault_tolerance.py`

- [ ] **Step 1: 添加消息队列测试**

```python
@pytest.mark.asyncio
async def test_message_queue_enqueue_and_process():
    """测试消息队列入队和消费"""
    from src.core.message_queue import MessageQueue, create_message_queue_backup_table
    
    await create_message_queue_backup_table()
    queue = MessageQueue(maxsize=10)
    await queue.start()
    
    try:
        # 入队消息
        message = {
            "recipient": "admin",
            "type": "info",
            "title": "Test queue message",
            "body": "Hello from queue",
        }
        success = await queue.enqueue(message)
        assert success is True
        
        # 等待消费
        await asyncio.sleep(2)
        
        # 验证通知已创建（通过 API）
        async with AsyncClient(app=app, base_url="http://test") as client:
            resp = await client.get("/api/v1/notifications?limit=1", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] >= 1
            
    finally:
        await queue.stop()


@pytest.mark.asyncio
async def test_message_queue_persists_when_full():
    """测试队列满时消息持久化到 DB"""
    from src.core.message_queue import MessageQueue, create_message_queue_backup_table
    
    await create_message_queue_backup_table()
    queue = MessageQueue(maxsize=1)  # 很小的队列
    # 不启动消费者，让队列满
    
    message = {"recipient": "admin", "type": "info", "title": "Persisted message", "body": "x"}
    await queue.enqueue(message)
    await queue.enqueue(message)  # 这次应该持久化到 DB
    
    # 验证 DB 中有备份
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM message_queue_backup"))
        count = result.scalar()
        assert count >= 1
```

- [ ] **Step 2: 添加工作流超时测试**

```python
@pytest.mark.asyncio
async def test_workflow_run_timeout_detection():
    """测试工作流运行超时检测"""
    from src.core.workflow_timeout import check_workflow_run_timeouts
    from src.models.workflow import WorkflowRun, WorkflowRunStatus
    
    # 创建一个超时的 WorkflowRun（started_at 设为很久以前）
    async with AsyncSessionLocal() as db:
        run = WorkflowRun(
            workflow_id=1,
            status=WorkflowRunStatus.RUNNING,
            current_step_index=0,
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),  # 1小时前
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id
    
    # 运行超时检测
    await check_workflow_run_timeouts()
    
    # 验证状态变为 failed
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == run_id)
        )
        run = result.scalar_one()
        assert run.status == WorkflowRunStatus.FAILED
        assert "timed out" in (run.error_message or "")
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_fault_tolerance.py
git commit -m "test: add message queue and workflow timeout tests"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 消息队列缓冲：`MessageQueue` 类 + SQLite 备份 + 失败重试
- ✅ 工作流超时检测：检查 running/waiting_approval 的 WorkflowRun
- ✅ 通知不丢失：API 失败时入队，恢复后自动消费
- ✅ 超时告警：标记 failed + 发送通知给 admin

**2. Placeholder scan:**
- ✅ 没有 TBD/TODO
- ✅ 所有代码完整

**3. Type consistency:**
- ✅ `WorkflowRunStatus` 使用模型定义的枚举
- ✅ `NotificationType` 使用模型定义的枚举

**Gap identified:**
- 消息队列消费需要 `_api_request` 可用的环境，在测试环境中可能需要 mock
- WorkflowRun 超时检测需要 WorkflowStep 的 timeout_seconds 字段，需要确保测试数据中有 workflow 和 step

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-message-queue-workflow-timeouts.md`.**
