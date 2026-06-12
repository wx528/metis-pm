"""轻量级消息队列 — 内存缓冲 + SQLite 持久化

当后端 API 暂时不可用时，通知消息写入队列，恢复后自动消费。
支持最大重试次数，超过后进入死信记录。
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

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # 指数退避基础延迟（秒）


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

    async def _persist_to_db(self, message: dict, retry_count: int = 0):
        """将消息持久化到 SQLite 备份表"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("""
                    INSERT INTO message_queue_backup (payload, created_at, retry_count)
                    VALUES (:payload, :created_at, :retry_count)
                """), {
                    "payload": json.dumps(message),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "retry_count": retry_count,
                })
                await db.commit()
                logger.warning(f"Message persisted to DB backup: {message.get('title', '?')}")
        except Exception as e:
            logger.error(f"Failed to persist message to DB: {e}")

    async def _move_to_dead_letter(self, message: dict, retry_count: int, error: str):
        """将超过最大重试次数的消息移入死信记录"""
        logger.error(f"Message exceeded max retries ({retry_count}), moving to dead letter: {message.get('title', '?')}")
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS message_queue_dead_letter (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payload TEXT NOT NULL,
                        retry_count INTEGER NOT NULL,
                        last_error TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await db.execute(text("""
                    INSERT INTO message_queue_dead_letter (payload, retry_count, last_error, created_at)
                    VALUES (:payload, :retry_count, :last_error, :created_at)
                """), {
                    "payload": json.dumps(message),
                    "retry_count": retry_count,
                    "last_error": error[:500],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to write dead letter: {e}")

    async def _consume(self):
        """消费队列中的消息"""
        while self._running:
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                retry_count = message.pop("_retry_count", 0)
                await self._process_message(message, retry_count)
            except asyncio.TimeoutError:
                # 检查 DB 备份中是否有消息
                await self._process_db_backup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message processing error: {e}")

    async def _process_message(self, message: dict, retry_count: int = 0):
        """处理单条消息：创建通知，失败后指数退避重试，超过次数进死信"""
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
            retry_count += 1
            if retry_count > MAX_RETRIES:
                await self._move_to_dead_letter(message, retry_count, str(e))
                return
            delay = RETRY_BASE_DELAY * (2 ** (retry_count - 1))
            logger.warning(f"Message processing failed (attempt {retry_count}/{MAX_RETRIES}), retry in {delay}s: {e}")
            await asyncio.sleep(delay)
            # 重试时携带重试计数
            message["_retry_count"] = retry_count
            await self.enqueue(message)

    async def _process_db_backup(self):
        """处理 SQLite 备份表中的消息"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(text("""
                    SELECT id, payload, retry_count FROM message_queue_backup
                    ORDER BY created_at LIMIT 10
                """))
                rows = result.fetchall()
                for row in rows:
                    msg_id, payload, retry_count = row
                    message = json.loads(payload)
                    try:
                        await self._process_message(message, retry_count or 0)
                        # 处理成功后删除备份
                        await db.execute(text(
                            "DELETE FROM message_queue_backup WHERE id = :id"
                        ), {"id": msg_id})
                    except Exception as e:
                        logger.error(f"DB backup message {msg_id} processing failed: {e}")
                        # 更新重试计数
                        new_count = (retry_count or 0) + 1
                        if new_count > MAX_RETRIES:
                            await self._move_to_dead_letter(message, new_count, str(e))
                            await db.execute(text(
                                "DELETE FROM message_queue_backup WHERE id = :id"
                            ), {"id": msg_id})
                        else:
                            await db.execute(text(
                                "UPDATE message_queue_backup SET retry_count = :rc WHERE id = :id"
                            ), {"rc": new_count, "id": msg_id})
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
