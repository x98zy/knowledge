from faststream.middlewares import AckPolicy
from sqlalchemy import case, func, select, update

from common.const import EMBED_ERROR_CACHE, EMBED_RETRY_CACHE
from common.entites import Document
from common.enum import FileStatus, SegmentStatus
from common.retry import RetryLimitExceeded, clear_retry_attempt, incr_retry_attempt, is_retryable
from config.settings import settings
from core.index_processor.constant.index_type import IndexType
from core.index_processor.index_processor_factory import IndexProcessorFactory
from core.vectordb.factory import VectorFactory
from extensions.ext_db import db
from extensions.ext_log import logger
from extensions.ext_redis import redis_client
from models.dataset import Dataset, ProcessRule
from models.document import ChildSegment, FileSegments, KbFile

from .app import broker
from .entites import EmbedMessage


async def update_segment_status(id_map: dict) -> bool:
    if not id_map:
        return False
    try:
        whens = [(FileSegments.id == seg_id, point_id) for seg_id, point_id in id_map.items()]
        stmt = (
            update(FileSegments)
            .where(FileSegments.id.in_(id_map.keys()))
            .values(point_id=case(*whens, else_=FileSegments.point_id), status=SegmentStatus.COMPLETED.value)
        )
        await db.session.execute(stmt)
        await db.session.commit()
        return True
    except Exception:
        await db.session.rollback()
        logger.exception("更新分段状态失败")
        return False


async def update_child_segment_status(child_id_map: dict) -> bool:
    if not child_id_map:
        return False
    try:
        whens = [(ChildSegment.id == seg_id, point_id) for seg_id, point_id in child_id_map.items()]
        stmt = (
            update(ChildSegment)
            .where(ChildSegment.id.in_(child_id_map.keys()))
            .values(point_id=case(*whens, else_=ChildSegment.point_id), status=SegmentStatus.COMPLETED.value)
        )
        await db.session.execute(stmt)
        await db.session.commit()

        return True
    except Exception:
        await db.session.rollback()
        logger.exception("更新子分段状态失败")
        return False


async def update_parent_segment_status(kb_file_id: str) -> bool:
    """根据子分段的状态去更新父分段的状态"""
    query = (
        select(ChildSegment.parent_id, func.count(ChildSegment.id))
        .filter(ChildSegment.file_id == kb_file_id, ChildSegment.deleted == 0)
        .group_by(ChildSegment.parent_id)
    )
    results = await db.session.execute(query)
    results = results.all()
    segment_map = {}
    for row in results:
        segment_map[row[0]] = row[1]
    for segment_id in segment_map:
        success_count_query = select(func.count(ChildSegment.id)).where(
            ChildSegment.parent_id == segment_id,
            ChildSegment.file_id == kb_file_id,
            ChildSegment.deleted == 0,
            ChildSegment.status == SegmentStatus.COMPLETED.value,
        )
        success_count = await db.session.execute(success_count_query)
        success_count = success_count.scalar_one()
        if success_count == segment_map[segment_id]:
            smt = (
                update(FileSegments)
                .where(FileSegments.id == segment_id, FileSegments.deleted == 0)
                .values(status=SegmentStatus.COMPLETED.value)
            )
            await db.session.execute(smt)
            await db.session.commit()


async def update_segments_error(documents: list[Document]):
    ids = []
    child_ids = []
    for document in documents:
        if document.id:
            ids.append(document.id)
        if document.children:
            for child in document.children:
                if child.id:
                    child_ids.append(child.id)
    if ids:
        stmt = update(FileSegments).where(FileSegments.id.in_(ids)).values(status=SegmentStatus.ERROR.value)
        await db.session.execute(stmt)
    if child_ids:
        stmt = update(ChildSegment).where(ChildSegment.id.in_(child_ids)).values(status=SegmentStatus.ERROR.value)
        await db.session.execute(stmt)
    await db.session.commit()


async def check_file_and_update(kb_file_id: str):
    """检查当前文件下所有分段的状态并且更新文件状态"""
    segment_count_query = select(func.count(FileSegments.id)).filter(
        FileSegments.file_id == kb_file_id, FileSegments.deleted == 0
    )
    segment_count = await db.session.execute(segment_count_query)
    segment_count = segment_count.scalar_one()

    success_count_query = select(func.count(FileSegments.id)).filter(
        FileSegments.file_id == kb_file_id,
        FileSegments.deleted == 0,
        FileSegments.status == SegmentStatus.COMPLETED.value,
    )
    success_count = await db.session.execute(success_count_query)
    success_count = success_count.scalar_one()

    error_count_query = select(func.count(FileSegments.id)).filter(
        FileSegments.file_id == kb_file_id,
        FileSegments.deleted == 0,
        FileSegments.status == SegmentStatus.ERROR.value,
    )
    error_count = await db.session.execute(error_count_query)
    error_count = error_count.scalar_one()

    # 更新文件状态为索引中
    if success_count > 0 and success_count < segment_count:
        smt = (
            update(KbFile).filter(KbFile.id == kb_file_id, KbFile.deleted == 0).values(status=FileStatus.INDEXING.value)
        )
        await db.session.execute(smt)
        await db.session.commit()

    # 更新文件状态为失败
    if error_count > 0:
        smt = update(KbFile).filter(KbFile.id == kb_file_id, KbFile.deleted == 0).values(status=FileStatus.FAILED.value)
        await db.session.execute(smt)
        await db.session.commit()

    # 更新文件状态为成功
    if success_count and segment_count and success_count == segment_count:
        smt = (
            update(KbFile)
            .filter(KbFile.id == kb_file_id, KbFile.deleted == 0)
            .values(status=FileStatus.SUCCESS.value, failed_reason=None)
        )
        await db.session.execute(smt)
        await db.session.commit()


async def clean_batch_data(docs: list[Document], kb_id: str):
    logger.warning(f"知识库 kb_id={kb_id} 向量化存在失败，触发kafka重试")
    query = select(Dataset).filter(Dataset.id == kb_id, Dataset.deleted == 0)
    dataset = await db.session.execute(query)
    dataset = dataset.scalars().first()
    if not dataset:
        logger.warning(f"Dataset with id {kb_id} not found.")
        return
    ids = []
    for doc in docs:
        if doc.id:
            ids.append(doc.id)
        if doc.children:
            for child_doc in doc.children:
                if child_doc.id:
                    ids.append(child_doc.id)
    segments_query = (
        select(FileSegments)
        .filter(FileSegments.id.in_(ids), FileSegments.deleted == 0)
        .with_only_columns(FileSegments.point_id)
    )
    point_ids = await db.session.execute(segments_query)
    point_ids = point_ids.scalars().all()

    child_segments_query = (
        select(ChildSegment)
        .filter(ChildSegment.id.in_(ids), ChildSegment.deleted == 0)
        .with_only_columns(ChildSegment.point_id)
    )
    child_point_ids = await db.session.execute(child_segments_query)
    child_point_ids = child_point_ids.scalars().all()

    point_ids = list(filter(lambda x: x is not None, point_ids))
    child_point_ids = list(filter(lambda x: x is not None, child_point_ids))
    point_ids.extend(child_point_ids)
    if point_ids:
        vector_factory = VectorFactory(dataset)
        await vector_factory.delete_by_ids(point_ids)
    stmt = (
        update(FileSegments).where(FileSegments.id.in_(ids)).values(status=SegmentStatus.WAITING.value, point_id=None)
    )
    await db.session.execute(stmt)
    stmt = (
        update(ChildSegment).where(ChildSegment.id.in_(ids)).values(status=SegmentStatus.WAITING.value, point_id=None)
    )
    await db.session.execute(stmt)
    await db.session.commit()


@broker.subscriber(
    settings.EMBED_TOPIC,
    group_id=settings.BROKER_GROUP_ID,
    auto_offset_reset=settings.BROKER_AUTO_OFFSET_RESET,
    max_poll_records=settings.BROKER_MAX_PULL_RECORDS,
    max_workers=settings.EMBED_MAX_WORKERS,
    # 放宽 aiokafka 会话/心跳/轮询超时，避免长任务期间被 coordinator 踢出组触发 rebalance 风暴
    session_timeout_ms=settings.BROKER_SESSION_TIMEOUT_MS,
    heartbeat_interval_ms=settings.BROKER_HEARTBEAT_INTERVAL_MS,
    max_poll_interval_ms=settings.BROKER_MAX_POLL_INTERVAL_MS,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def embed(message: EmbedMessage):
    retry_key = EMBED_RETRY_CACHE.format(batch_id=message.batch_id)
    try:
        error_key = EMBED_ERROR_CACHE.format(batch_id=message.batch_id)
        if await redis_client.get(error_key):
            await clean_batch_data(message.documents, message.kb_id)
            await redis_client.delete(error_key)
        dataset_query = select(Dataset).filter(Dataset.id == message.kb_id, Dataset.deleted == 0)
        dataset = await db.session.execute(dataset_query)
        dataset = dataset.scalars().first()
        if not dataset:
            raise RuntimeError("知识库不存在")
        file_query = select(KbFile).filter(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
        kb_file = await db.session.execute(file_query)
        kb_file = kb_file.scalars().first()
        if not kb_file:
            raise RuntimeError("知识库文件不存在")
        query = select(ProcessRule).filter(ProcessRule.kb_file_id == message.kb_file_id, ProcessRule.deleted == 0)
        process_rule = await db.session.execute(query)
        process_rule = process_rule.scalars().first()
        if not process_rule:
            raise RuntimeError("分段规则不存在")
        index_factory = IndexProcessorFactory(process_rule.segment_mode)
        index_processor = index_factory.init_index_processor()
        child_id_map = {}
        id_map = {}
        # 父子分段
        if process_rule.segment_mode == IndexType.PARENT_CHILD_INDEX.value:
            pks = await index_processor.load(dataset, message.documents)
            for doc in message.documents:
                for i, child_doc in enumerate(doc.children):
                    child_id_map[child_doc.id] = pks[i]
        else:
            pks = await index_processor.load(dataset, message.documents)
            for i, doc in enumerate(message.documents):
                id_map[doc.id] = pks[i]
        if id_map:
            await update_segment_status(id_map)
        if child_id_map:
            await update_child_segment_status(child_id_map)
        if process_rule.segment_mode == IndexType.PARENT_CHILD_INDEX.value:
            await update_parent_segment_status(message.kb_file_id)
        await check_file_and_update(message.kb_file_id)
        await clear_retry_attempt(retry_key)
    except Exception as e:
        if is_retryable(e):
            # 瞬时错误（网络抖动/超时/429/5xx/连接失败）：文件保留 PROCESSING 状态，
            # 写批次清理标记后原样抛出（保留异常类型），由 NACK_ON_ERROR 触发 Kafka 重投
            try:
                await incr_retry_attempt(retry_key, settings.BROKER_MAX_RETRY, settings.BROKER_RETRY_KEY_TTL)
            except RetryLimitExceeded as retry_ex:
                logger.warning(
                    f"embed worker 重试次数超过限制，触发文件失败 kb_file_id={message.kb_file_id} err={e}",
                    exc_info=retry_ex,
                )
                await clear_retry_attempt(retry_key)
                smt = (
                    update(KbFile)
                    .filter(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
                    .values(status=FileStatus.FAILED.value, failed_reason=str(e)[0:500])
                )
                await db.session.execute(smt)
                await db.session.commit()
            logger.warning(
                f"embed worker 发生瞬时错误，触发 Kafka 重试 kb_file_id={message.kb_file_id} err={e}",
                exc_info=e,
            )
            error_key = EMBED_ERROR_CACHE.format(batch_id=message.batch_id)
            await redis_client.set(error_key, 1, ex=600)
            raise
        await db.session.rollback()
        # 更新分段状态为失败
        await update_segments_error(message.documents)
        logger.exception("文件向量化失败")
        smt = (
            update(KbFile)
            .filter(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
            .values(status=FileStatus.FAILED.value, failed_reason=str(e)[0:500])
        )
        await db.session.execute(smt)
        await db.session.commit()
    finally:
        await db.session.close()
