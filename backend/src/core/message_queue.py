"""轻量级消息队列 — SQLite 持久化优先（写入即落盘）

所有消息先写入 SQLite，再由消费者异步处理。
处理成功后从队列中删除，失败则指数退避重试，超过次数进死信。

优势：
- 写入即落盘，backend 重启不丢消息
- 内存仅做通知信号（asyncio.Event），不存消息体
- 消费确认：处理成功才删除，失败自动重试
- 死信队列：超过重试次数的消息移入死信表
"""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # 指数退避基础延迟（秒）
BATCH_SIZE = 20  # 每次从 DB 拉取的消息数


class MessageQueue:
    """基于 SQLite 持久化的消息队列，内存仅做通知信号"""

    def __init__(self):
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._notify = asyncio.Event()  # 新消息通知信号

    async def start(self):
        """启动队列消费者"""
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume())
        logger.info("Message queue consumer started (persist-first mode)")

    async def stop(self):
        """停止队列消费者"""
        self._running = False
        self._notify.set()  # 唤醒消费者以便退出
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Message queue consumer stopped")

    async def enqueue(self, message: dict) -> bool:
        """将消息入队 — 写入即落盘，不丢数据"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("""
                    INSERT INTO message_queue (payload, status, created_at)
                    VALUES (:payload, 'pending', :created_at)
                """), {
                    "payload": json.dumps(message, ensure_ascii=False),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                await db.commit()
            # 通知消费者有新消息
            self._notify.set()
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return False

    async def _consume(self):
        """消费队列中的消息"""
        while self._running:
            try:
                # 等待新消息通知或超时轮询
                try:
                    await asyncio.wait_for(self._notify.wait(), timeout=5.0)
                    self._notify.clear()
                except asyncio.TimeoutError:
                    pass

                if not self._running:
                    break

                # 从 DB 拉取待处理消息
                await self._process_pending_messages()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message consumer error: {e}")
                await asyncio.sleep(1)

    async def _process_pending_messages(self):
        """从 DB 拉取并处理待处理消息"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            async with AsyncSessionLocal() as db:
                # 拉取 pending 且已到重试时间的消息
                result = await db.execute(text("""
                    SELECT id, payload, retry_count FROM message_queue
                    WHERE status = 'pending'
                      AND (next_retry_at IS NULL OR next_retry_at <= :now)
                    ORDER BY created_at
                    LIMIT :limit
                """), {"limit": BATCH_SIZE, "now": now})
                rows = result.fetchall()

                if not rows:
                    return

                for row in rows:
                    msg_id, payload, retry_count = row
                    message = json.loads(payload)

                    try:
                        await self._deliver_message(message)
                        # 处理成功，从队列中删除
                        await db.execute(text(
                            "DELETE FROM message_queue WHERE id = :id"
                        ), {"id": msg_id})
                        logger.info(f"Message #{msg_id} delivered successfully")
                    except Exception as e:
                        # 处理失败，更新重试计数
                        new_count = (retry_count or 0) + 1
                        if new_count > MAX_RETRIES:
                            # 超过重试次数，移入死信
                            await self._move_to_dead_letter(db, msg_id, message, new_count, str(e))
                            await db.execute(text(
                                "DELETE FROM message_queue WHERE id = :id"
                            ), {"id": msg_id})
                        else:
                            # 指数退避：设置下次可处理时间，不阻塞当前批次
                            delay = RETRY_BASE_DELAY * (2 ** (new_count - 1))
                            next_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
                            await db.execute(text("""
                                UPDATE message_queue
                                SET retry_count = :rc, status = 'pending',
                                    next_retry_at = :next_at
                                WHERE id = :id
                            """), {
                                "rc": new_count,
                                "next_at": next_at,
                                "id": msg_id,
                            })
                            logger.warning(
                                f"Message #{msg_id} delivery failed "
                                f"(attempt {new_count}/{MAX_RETRIES}), "
                                f"next retry after {next_at}: {e}"
                            )

                await db.commit()

        except Exception as e:
            logger.error(f"Pending messages processing error: {e}")

    async def _deliver_message(self, message: dict):
        """投递消息：创建通知"""
        from src.core.notification import create_notification
        from src.models.notification import NotificationType

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
            await db.commit()

    async def _move_to_dead_letter(
        self, db: AsyncSession, msg_id: int,
        message: dict, retry_count: int, error: str,
    ):
        """将超过最大重试次数的消息移入死信记录"""
        logger.error(
            f"Message #{msg_id} exceeded max retries ({retry_count}), "
            f"moving to dead letter: {message.get('title', '?')}"
        )
        try:
            await db.execute(text("""
                INSERT INTO message_queue_dead_letter (payload, retry_count, last_error, created_at)
                VALUES (:payload, :retry_count, :last_error, :created_at)
            """), {
                "payload": json.dumps(message, ensure_ascii=False),
                "retry_count": retry_count,
                "last_error": error[:500],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to write dead letter: {e}")

    async def get_stats(self) -> dict:
        """获取队列统计"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(text(
                    "SELECT COUNT(*) FROM message_queue WHERE status = 'pending'"
                ))
                pending = result.scalar() or 0

                result = await db.execute(text(
                    "SELECT COUNT(*) FROM message_queue_dead_letter"
                ))
                dead = result.scalar() or 0

                return {"pending": pending, "dead_letter": dead}
        except Exception:
            return {"pending": 0, "dead_letter": 0}


# 全局队列实例
message_queue = MessageQueue()


async def create_message_queue_tables():
    """创建消息队列相关表（如果不存在）"""
    async with AsyncSessionLocal() as db:
        # 主队列表
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS message_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                next_retry_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # 死信表
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS message_queue_dead_letter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                retry_count INTEGER NOT NULL,
                last_error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # 迁移：如果旧备份表有数据，迁移到新表
        try:
            result = await db.execute(text(
                "SELECT COUNT(*) FROM message_queue_backup"
            ))
            backup_count = result.scalar() or 0
            if backup_count > 0:
                await db.execute(text("""
                    INSERT INTO message_queue (payload, status, retry_count, created_at)
                    SELECT payload, 'pending', retry_count, created_at
                    FROM message_queue_backup
                """))
                await db.execute(text("DELETE FROM message_queue_backup"))
                logger.info(f"Migrated {backup_count} messages from backup to main queue")
        except Exception:
            # 旧表不存在，忽略
            pass

        await db.commit()
