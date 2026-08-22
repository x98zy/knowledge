from datetime import datetime

from sqlalchemy import select, update
from uuid_extensions import uuid7

from common.entites import ParentMode
from common.enum import FileStatus
from common.error import CustomException
from config.settings import settings
from core.utils.page import Page, PaginationInput, paginate
from core.vectordb.factory import VectorFactory
from extensions.ext_db import db
from extensions.ext_log import logger
from models.dataset import Dataset, ProcessRule
from models.document import ChildSegment, FileSegments, KbFile, UploadFile
from models.outbox import OutboxMessage
from models.user import User
from workers.app import send_broker_message
from workers.entites import ExtracMessage


class FileService:
    @classmethod
    async def delete_file(cls, file_id: str, user_id: str) -> bool:
        try:
            user_query = select(User).filter(User.id == user_id, User.deleted == 0)
            user = await db.session.execute(user_query)
            user = user.scalars().first()
            if not user:
                raise CustomException("当前用户不存在")
            file_query = select(KbFile).where(KbFile.id == file_id, KbFile.deleted == 0)
            file = await db.session.execute(file_query)
            file = file.scalars().first()
            if not file:
                raise CustomException("文件不存在")
            dataset_query = select(Dataset).where(Dataset.id == file.dataset_id, Dataset.deleted == 0)
            dataset = await db.session.execute(dataset_query)
            dataset = dataset.scalars().first()
            if not dataset:
                raise CustomException("所属知识库不存在")
            if file.created_by_id != user_id:
                raise CustomException("您没有当前文件的权限")
            segment_point_query = (
                select(FileSegments)
                .where(FileSegments.file_id == file_id, FileSegments.deleted == 0)
                .with_only_columns(FileSegments.point_id)
            )
            point_ids = await db.session.execute(segment_point_query)
            point_ids = point_ids.scalars().all()

            child_point_query = (
                select(ChildSegment)
                .where(ChildSegment.file_id == file_id, ChildSegment.deleted == 0)
                .with_only_columns(ChildSegment.point_id)
            )
            child_point_ids = await db.session.execute(child_point_query)
            child_point_ids = child_point_ids.scalars().all()
            point_ids = list(filter(lambda x: x is not None, point_ids))
            child_point_ids = list(filter(lambda x: x is not None, child_point_ids))
            delete_ids = []
            if point_ids:
                delete_ids.extend(point_ids)
            if child_point_ids:
                delete_ids.extend(child_point_ids)
            if delete_ids:
                vector = VectorFactory(dataset)
                logger.info(f"删除文件 id={file_id} 中 {len(delete_ids)} 个向量片段")
                await vector.delete_by_ids(delete_ids)
            file_delete_query = (
                update(KbFile)
                .where(KbFile.id == file_id, KbFile.deleted == 0)
                .values(deleted=int(datetime.now().timestamp()))
            )
            segments_update_query = (
                update(FileSegments)
                .where(FileSegments.deleted == 0, FileSegments.file_id == file_id)
                .values(deleted=int(datetime.now().timestamp()))
            )
            child_update_query = (
                update(ChildSegment)
                .where(ChildSegment.deleted == 0, ChildSegment.file_id == file_id)
                .values(deleted=int(datetime.now().timestamp()))
            )
            rule_update_query = (
                update(ProcessRule)
                .filter(ProcessRule.kb_file_id == file_id, ProcessRule.deleted == 0)
                .values(deleted=int(datetime.now().timestamp()))
            )
            upload_delete_query = (
                update(UploadFile)
                .where(UploadFile.file_key == file.file_key, UploadFile.deleted == 0)
                .values(deleted=int(datetime.now().timestamp()))
            )
            await db.session.execute(file_delete_query)
            await db.session.execute(segments_update_query)
            await db.session.execute(child_update_query)
            await db.session.execute(rule_update_query)
            await db.session.execute(upload_delete_query)
            await db.session.commit()
            return True
        except CustomException:
            await db.session.rollback()
            raise
        except Exception:
            logger.exception("删除文件失败")
            await db.session.rollback()
            raise CustomException(message="删除文件失败") from None

    @classmethod
    async def file_list(
        cls, user_id: str, knowledge_id: str, page: int = 1, page_size: int = 10, keyword: str | None = None
    ) -> Page[KbFile]:
        dataset_query = select(Dataset).filter(Dataset.id == knowledge_id, Dataset.deleted == 0)
        datasets = await db.session.execute(dataset_query)
        dataset = datasets.scalars().first()
        if not dataset:
            raise CustomException(message="知识库不存在")
        if dataset.created_by_id != user_id:
            raise CustomException(message="您没有当前知识库的权限")
        query = select(KbFile).where(KbFile.dataset_id == knowledge_id, KbFile.deleted == 0)
        if keyword:
            query = query.where(KbFile.file_name.contains(keyword))
        page_info = await paginate(
            query,
            PaginationInput(page=page, page_size=page_size),
        )
        return page_info

    @classmethod
    async def create_file(
        cls,
        user_id: str,
        dataset_id: str,
        file_key: str,
        segment_mode: str,
        pre_rule: str,
        max_tokens: int,
        overlap: int,
        delimiter: str,
        parent_mode: str | None = None,
        child_delimiter: str | None = None,
        child_overlap: int | None = None,
        child_max_tokens: int | None = None,
        enable_semantic: bool = False,
    ):
        try:
            user_query = select(User).filter(User.id == user_id, User.deleted == 0)
            user = await db.session.execute(user_query)
            user = user.scalars().first()
            if not user:
                raise CustomException("当前用户不存在")
            dataset_query = select(Dataset).filter(Dataset.id == dataset_id, Dataset.deleted == 0)
            dataset = await db.session.execute(dataset_query)
            dataset = dataset.scalars().first()
            if not dataset:
                raise CustomException(message="知识库不存在")
            if dataset.created_by_id != user_id:
                raise CustomException(message="您没有当前知识库的权限")
            upload_file_query = select(UploadFile).filter(UploadFile.file_key == file_key, UploadFile.deleted == 0)
            upload_file = await db.session.execute(upload_file_query)
            upload_file = upload_file.scalars().first()
            if not upload_file:
                raise CustomException(message="上传文件不存在")
            kb_file_id = str(uuid7())
            kb_file = KbFile(
                id=kb_file_id,
                dataset_id=dataset_id,
                enable_semantic=enable_semantic,
                file_name=upload_file.file_name,
                file_key=file_key,
                status=FileStatus.WAITING.value,
                created_by_id=user.id,
                updated_by_id=user.id,
                created_by=user.username,
                updated_by=user.username,
            )
            db.session.add(kb_file)
            if parent_mode and parent_mode not in [ParentMode.FULL_DOC.value, ParentMode.PARAGRAPH.value]:
                raise CustomException(message="父分段规则不合法")
            process_rule = ProcessRule(
                kb_file_id=kb_file_id,
                pre_rule=pre_rule,
                segment_mode=segment_mode,
                max_tokens=max_tokens,
                overlap=overlap,
                delimiter=delimiter,
                parent_mode=parent_mode,
                child_delimiter=child_delimiter,
                child_overlap=child_overlap,
                child_max_tokens=child_max_tokens,
                created_by_id=user.id,
                updated_by_id=user.id,
                created_by=user.username,
                updated_by=user.username,
            )
            db.session.add(process_rule)
            if settings.START_BROKER_OUTBOX:
                outbox_record = OutboxMessage(
                    topic=settings.EXTRACTOR_TOPIC,
                    payload=ExtracMessage(kb_file_id=kb_file_id, metadata={}).model_dump(),
                    created_by_id=user.id,
                    updated_by_id=user.id,
                    created_by=user.username,
                    updated_by=user.username,
                )
                db.session.add(outbox_record)
            await db.session.commit()
            await send_broker_message(
                topic=settings.EXTRACTOR_TOPIC,
                message=ExtracMessage(kb_file_id=kb_file_id, metadata={}).model_dump(),
            )
            return True
        except Exception as e:
            logger.exception("上传文件失败")
            await db.session.rollback()
            raise CustomException(message=f"创建文件失败: {e!s}") from None
