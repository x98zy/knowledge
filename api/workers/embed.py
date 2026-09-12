from sqlalchemy import case, func, select, update

from common.entites import Document
from common.enum import FileStatus, SegmentStatus
from config.settings import settings
from core.index_processor.constant.index_type import IndexType
from core.index_processor.index_processor_factory import IndexProcessorFactory
from extensions.ext_db import db
from extensions.ext_log import logger
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
            update(KbFile).filter(KbFile.id == kb_file_id, KbFile.deleted == 0).values(status=FileStatus.SUCCESS.value)
        )
        await db.session.execute(smt)
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
)
async def embed(message: EmbedMessage):
    try:
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
    except Exception as e:
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
