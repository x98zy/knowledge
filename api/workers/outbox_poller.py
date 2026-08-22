# api/workers/outbox_poller.py
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from common.enum import OutBoxStatus
from extensions.ext_db import async_session_factory
from extensions.ext_log import logger
from models.outbox import OutboxMessage

MAX_RETRY = 10
BATCH_SIZE = 100
POLL_INTERVAL_SECONDS = 5


async def poll_outbox():
    """轮询 outbox 表，把 pending 消息推到 Kafka"""
    from .app import broker

    while True:
        try:
            async with async_session_factory() as session:
                # SKIP LOCKED 防止多实例并发抢同一行
                stmt = (
                    select(OutboxMessage)
                    .where(
                        OutboxMessage.status == OutBoxStatus.PENDING.value,
                        OutboxMessage.retry_count < MAX_RETRY,
                    )
                    .order_by(OutboxMessage.created_time)
                    .limit(BATCH_SIZE)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                messages = result.scalars().all()

                for msg in messages:
                    try:
                        await broker.publish(
                            message=msg.payload,
                            topic=msg.topic,
                        )
                        # 发送成功，标记 sent
                        msg.status = OutBoxStatus.SENT.value
                    except Exception as e:
                        # 发送失败，记录重试，指数退避
                        msg.retry_count += 1
                        if msg.retry_count == MAX_RETRY:
                            msg.status = OutBoxStatus.FAILED.value
                        else:
                            msg.next_retry_at = datetime.utcnow() + timedelta(seconds=2**msg.retry_count)
                            logger.warning(f"Outbox msg {msg.id} publish failed, retry {msg.retry_count}: {e}")
                await session.commit()
        except Exception as e:
            logger.exception(f"Outbox poller error: {e}")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
