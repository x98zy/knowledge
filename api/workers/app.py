import asyncio

from faststream import FastStream
from faststream.kafka import KafkaBroker

from common.decorators import retry_until_success
from config.settings import settings

from .outbox_poller import poll_outbox

broker = KafkaBroker(settings.BROKER_URL)
app = FastStream(broker)


@app.after_startup
async def _start_poller():
    # 启动 outbox 轮询后台任务
    if settings.START_BROKER_OUTBOX:
        asyncio.create_task(poll_outbox())  # noqa: RUF006


@retry_until_success(interval=[1, 1, 1, 1])
async def send_broker_message(topic: str, message: dict):
    await broker.publish(topic=topic, message=message)


# 导入订阅者模块，使 @broker.subscribe 装饰器生效
from . import embed, extract, shard  # noqa: E402,F401
