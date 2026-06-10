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
