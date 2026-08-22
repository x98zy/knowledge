from sqlalchemy import select, update
from uuid_extensions import uuid7

from common.entites import ExtractSetting, UploadFile
from common.enum import FileStatus
from config.settings import settings
from core.index_processor.index_processor_factory import IndexProcessorFactory
from extensions.ext_db import db
from extensions.ext_log import logger
from models.dataset import ProcessRule
from models.document import ChildSegment, FileSegments, KbFile

from .app import broker, send_broker_message
from .entites import EmbedMessage, ExtracMessage


@broker.subscriber(
    settings.EXTRACTOR_TOPIC,
    group_id=settings.BROKER_GROUP_ID,
    auto_offset_reset=settings.BROKER_AUTO_OFFSET_RESET,
    max_poll_records=settings.BROKER_MAX_PULL_RECORDS,
    max_workers=settings.EXTRACT_MAX_WORKERS,
)
async def extract(message: ExtracMessage):
    try:
        query = select(KbFile).where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
        kb_file = await db.session.execute(query)
        kb_file = kb_file.scalars().first()
        if not kb_file:
            return
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
        for doc in tranform_documents:
            segment = FileSegments(
                id=str(uuid7()),
                file_id=kb_file.id,
                dataset_id=kb_file.dataset_id,
                content=doc.page_content,
                answer=doc.metadata.get("answer", ""),
                metadata_=doc.metadata,
            )
            segments.append(segment)
            doc.id = segment.id
            if doc.children:
                for child_doc in doc.children:
                    child_segment = ChildSegment(
                        id=str(uuid7()),
                        parent_id=segment.id,
                        file_id=kb_file.id,
                        dataset_id=kb_file.dataset_id,
                        content=child_doc.page_content,
                        metadata_=child_doc.metadata,
                    )
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
                    documents=batch_documents, kb_file_id=message.kb_file_id, kb_id=kb_file.dataset_id
                ).model_dump(),
            )
        logger.info(
            f"Extracted and transformed {len(tranform_documents)} documents for kb_file_id: {message.kb_file_id}"
        )
    except Exception as e:
        await db.session.rollback()
        smt = (
            update(KbFile)
            .where(KbFile.id == message.kb_file_id, KbFile.deleted == 0)
            .values(status=FileStatus.FAILED.value, failed_reason=f"文件解析失败: {str(e)[:500]}")
        )
        await db.session.execute(smt)
        await db.session.commit()
        logger.exception(f"Error processing message: {message}. Error: {e}")

    finally:
        await db.session.close()
