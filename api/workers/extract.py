from datetime import datetime

from faststream.middlewares import AckPolicy
from sqlalchemy import select, update
from uuid_extensions import uuid7

from common.const import EXTRACT_ERROR_CACHE, EXTRACT_RETRY_CACHE
from common.entites import ExtractSetting, UploadFile
from common.enum import FileStatus
from common.retry import RetryLimitExceeded, clear_retry_attempt, incr_retry_attempt, is_retryable
from config.settings import settings
from core.index_processor.index_processor_factory import IndexProcessorFactory
from core.vectordb.factory import VectorFactory
from extensions.ext_db import db
from extensions.ext_log import logger
from extensions.ext_redis import redis_client
from models.dataset import Dataset, ProcessRule
from models.document import ChildSegment, FileSegments, KbFile

from .app import broker, send_broker_message
from .entites import EmbedMessage, ExtracMessage


async def clean_batch_data(batch_id: str, kb_id: str):
    """清理同一批次的文件数据"""
    logger.warning(f"extract worker 发生错误，触发kafka重试 kb_id={kb_id}")
    query = select(Dataset).filter(Dataset.id == kb_id, Dataset.deleted == 0)
    dataset = await db.session.execute(query)
    dataset = dataset.scalars().first()
    if not dataset:
        logger.warning(f"Dataset with id {kb_id} not found.")
        return
    segments_query = (
        select(FileSegments)
        .filter(FileSegments.batch_id == batch_id, FileSegments.deleted == 0)
        .with_only_columns(FileSegments.point_id)
    )
    point_ids = await db.session.execute(segments_query)
    point_ids = point_ids.scalars().all()

    child_segments_query = (
        select(ChildSegment)
        .filter(ChildSegment.batch_id == batch_id, ChildSegment.deleted == 0)
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
    await db.session.execute(
        update(FileSegments)
        .where(FileSegments.batch_id == batch_id, FileSegments.deleted == 0)
        .values(deleted=int(datetime.now().timestamp()))
    )
    await db.session.execute(
        update(ChildSegment)
        .where(ChildSegment.batch_id == batch_id, ChildSegment.deleted == 0)
        .values(deleted=int(datetime.now().timestamp()))
    )
    await db.session.commit()


@broker.subscriber(
    settings.EXTRACTOR_TOPIC,
    group_id=settings.BROKER_GROUP_ID,
    auto_offset_reset=settings.BROKER_AUTO_OFFSET_RESET,
    max_poll_records=settings.BROKER_MAX_PULL_RECORDS,
    max_workers=settings.EXTRACT_MAX_WORKERS,
    # 放宽 aiokafka 会话/心跳/轮询超时，避免长任务期间被 coordinator 踢出组触发 rebalance 风暴
    session_timeout_ms=settings.BROKER_SESSION_TIMEOUT_MS,
    heartbeat_interval_ms=settings.BROKER_HEARTBEAT_INTERVAL_MS,
    max_poll_interval_ms=settings.BROKER_MAX_POLL_INTERVAL_MS,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def extract(message: ExtracMessage):
    try:
        query = select(KbFile).where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
        kb_file = await db.session.execute(query)
        kb_file = kb_file.scalars().first()
        if not kb_file:
            return
        error_key = EXTRACT_ERROR_CACHE.format(batch_id=message.batch_id)
        if await redis_client.get(error_key):
            await clean_batch_data(batch_id=message.batch_id, kb_id=kb_file.dataset_id)
            await redis_client.delete(error_key)
        # 获取分段规则
        query = select(ProcessRule).filter(ProcessRule.kb_file_id == message.kb_file_id, ProcessRule.deleted == 0)
        process_rule = await db.session.execute(query)
        process_rule = process_rule.scalars().first()
        if not process_rule:
            smt = (
                update(KbFile)
                .where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
                .values(status=FileStatus.FAILED.value, failed_reason="未找到分段规则")
            )
            await db.session.execute(smt)
            await db.session.commit()
            return
        # 将文件状态更新为解析中
        smt = (
            update(KbFile)
            .where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
            .values(status=FileStatus.PROCESSING.value)
        )
        await db.session.execute(smt)
        index_factory = IndexProcessorFactory(process_rule.segment_mode)
        index_processor = index_factory.init_index_processor()
        extract_settings = ExtractSetting(upload_file=UploadFile(file_key=kb_file.file_key))
        documents = await index_processor.extract(extract_settings)
        tranform_documents = await index_processor.transform(
            documents, process_rule=process_rule.tranform_rule.model_dump()
        )
        for document in tranform_documents:
            document.metadata = message.metadata or {}
        segments = []
        child_docs = []
        position = 1
        for doc in tranform_documents:
            segment = FileSegments(
                id=str(uuid7()),
                file_id=kb_file.id,
                dataset_id=kb_file.dataset_id,
                content=doc.page_content,
                answer=doc.metadata.get("answer", ""),
                metadata_=doc.metadata,
                position=position,
                batch_id=message.batch_id,  # 设置批次ID
            )
            position += 1
            segments.append(segment)
            doc.id = segment.id
            if doc.children:
                child_position = 1
                for child_doc in doc.children:
                    child_segment = ChildSegment(
                        id=str(uuid7()),
                        parent_id=segment.id,
                        file_id=kb_file.id,
                        dataset_id=kb_file.dataset_id,
                        content=child_doc.page_content,
                        metadata_=child_doc.metadata,
                        position=child_position,
                        batch_id=message.batch_id,  # 设置批次ID
                    )
                    child_position += 1
                    child_docs.append(child_segment)
                    child_doc.id = child_segment.id
        if segments:
            db.session.add_all(segments)
        if child_docs:
            db.session.add_all(child_docs)
        await db.session.commit()
        for i in range(0, len(tranform_documents), settings.EMBDED_BATCH_SIZE):
            batch_documents = tranform_documents[i : i + settings.EMBDED_BATCH_SIZE]
            await send_broker_message(
                topic=settings.EMBED_TOPIC,
                message=EmbedMessage(
                    documents=batch_documents,
                    kb_file_id=message.kb_file_id,
                    kb_id=kb_file.dataset_id,
                    batch_id=str(uuid7()),
                ).model_dump(),
            )
        logger.info(
            f"Extracted and transformed {len(tranform_documents)} documents for kb_file_id: {message.kb_file_id}"
        )
        # 处理成功（含重试后成功）：清理历史重试计数
        await clear_retry_attempt(EXTRACT_RETRY_CACHE.format(batch_id=message.batch_id))
    except Exception as e:
        await db.session.rollback()
        retry_key = EXTRACT_RETRY_CACHE.format(batch_id=message.batch_id)
        if is_retryable(e):
            # 瞬时错误（网络抖动/超时/429/5xx/连接失败）：计数 +1，未超上限则原样抛出由 NACK 重投
            try:
                attempt = await incr_retry_attempt(
                    retry_key, settings.BROKER_MAX_RETRY, settings.BROKER_RETRY_KEY_TTL
                )
            except RetryLimitExceeded:
                # 重试耗尽：文件保留/落为 FAILED 终态，消息正常 ACK 结束，不再重投
                await clear_retry_attempt(retry_key)
                logger.exception(
                    f"extract worker 瞬时错误重试已达上限({settings.BROKER_MAX_RETRY}次)，放弃: {message}"
                )
                smt = (
                    update(KbFile)
                    .where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
                    .values(
                        status=FileStatus.FAILED.value,
                        failed_reason=f"文件解析失败，重试{settings.BROKER_MAX_RETRY}次后仍失败: {str(e)[:300]}",
                    )
                )
                await db.session.execute(smt)
                await db.session.commit()
                return

            # 文件保留 PROCESSING 状态，写批次清理标记后原样抛出（保留异常类型），由 NACK_ON_ERROR 重投
            logger.warning(
                f"extract worker 发生瞬时错误，第 {attempt}/{settings.BROKER_MAX_RETRY} 次重试 "
                f"kb_file_id={message.kb_file_id} err={e}",
                exc_info=e,
            )
            error_key = EXTRACT_ERROR_CACHE.format(batch_id=message.batch_id)
            await redis_client.set(error_key, 1, ex=600)
            raise

        # 永久错误（文件损坏/格式不支持/参数非法/NotImplemented 等）：标记 FAILED 终态后正常返回，
        # FastStream 收到正常返回即 ACK，消息不再重投，避免毒消息无限循环与重复计费
        await clear_retry_attempt(retry_key)
        logger.exception(f"extract worker 发生永久错误，消息直接确认不重试: {message}")
        smt = (
            update(KbFile)
            .where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
            .values(status=FileStatus.FAILED.value, failed_reason=f"文件解析失败: {str(e)[:500]}")
        )
        await db.session.execute(smt)
        await db.session.commit()
        return
    finally:
        await db.session.close()
