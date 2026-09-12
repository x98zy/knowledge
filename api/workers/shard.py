from datetime import datetime

from faststream.middlewares import AckPolicy
from sqlalchemy import select, update

from config.settings import settings
from core.vectordb.factory import VectorFactory
from extensions.ext_db import db
from extensions.ext_log import logger
from models.dataset import Dataset
from models.document import ChildSegment, FileSegments

from .app import broker
from .entites import DeleteDatasetMessage


@broker.subscriber(
    settings.DELETE_DATASET_TOPIC,
    group_id=settings.BROKER_GROUP_ID,
    auto_offset_reset=settings.BROKER_AUTO_OFFSET_RESET,
    max_poll_records=settings.BROKER_MAX_PULL_RECORDS,
    max_workers=settings.DELETE_DATASET_MAX_WORKERS,
    # NACK_ON_ERROR 保证消费失败消息会重新投递
    ack_policy=AckPolicy.NACK_ON_ERROR,
    # 放宽 aiokafka 会话/心跳/轮询超时，避免长任务期间被 coordinator 踢出组触发 rebalance 风暴
    session_timeout_ms=settings.BROKER_SESSION_TIMEOUT_MS,
    heartbeat_interval_ms=settings.BROKER_HEARTBEAT_INTERVAL_MS,
    max_poll_interval_ms=settings.BROKER_MAX_POLL_INTERVAL_MS,
)
async def delete_dataset(message: DeleteDatasetMessage):
    try:
        # 这个worker消息处理是幂等的，即使是重复的消息也可以保证结果一致
        dateset_query = select(Dataset).filter(Dataset.id == message.kb_id)
        dataset = await db.session.execute(dateset_query)
        dataset = dataset.scalars().first()

        vector = VectorFactory(dataset)
        delete_query = (
            update(FileSegments)
            .where(FileSegments.dataset_id == message.kb_id, FileSegments.deleted == 0)
            .values(deleted=int(datetime.now().timestamp()))
        )
        delete_query_1 = (
            update(ChildSegment)
            .where(ChildSegment.dataset_id == message.kb_id, ChildSegment.deleted == 0)
            .values(deleted=int(datetime.now().timestamp()))
        )
        await db.session.execute(delete_query)
        await db.session.execute(delete_query_1)
        await db.session.commit()
        # 限制 drop 超时，避免 Milvus 异常时 grpc 无限挂起占住 worker
        await vector.drop_collection(timeout=60)
        # TODO 这里可以加一个兜底补偿机制，加一个30分钟之后的定时触发任务，去检查向量库记录有没有被真正删除，没有删除再尝试删除
    except Exception as e:
        logger.exception("删除知识库失败")
        raise RuntimeError("删除知识库失败") from e
    finally:
        await db.session.close()
