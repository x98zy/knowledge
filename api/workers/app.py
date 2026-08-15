from faststream import FastStream
from faststream.kafka import KafkaBroker

from config.settings import settings

broker = KafkaBroker(settings.BROKER_URL)
app = FastStream(broker)

# 导入订阅者模块，使 @broker.subscribe 装饰器生效
from . import embed, extract  # noqa: E402,F401
