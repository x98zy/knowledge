from config.settings import settings

from .app import broker
from .entites import EmbedMessage


@broker.subscriber(
    settings.EMBED_TOPIC,
    group_id=settings.BROKER_GROUP_ID,
    auto_offset_reset=settings.BROKER_AUTO_OFFSET_RESET,
    max_poll_records=settings.BROKER_MAX_PULL_RECORDS,
    max_workers=settings.EMBED_MAX_WORKERS,
)
async def embed(message: EmbedMessage):
    pass
