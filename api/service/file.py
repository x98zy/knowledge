from sqlalchemy import select
from uuid_extensions import uuid7

from common.entites import ParentMode
from common.enum import FileStatus
from common.error import CustomException
from config.settings import settings
from core.utils.page import Page, PaginationInput, paginate
from extensions.ext_db import db
from extensions.ext_log import logger
from models.dataset import Dataset, ProcessRule
from models.document import KbFile, UploadFile
from models.user import User
from workers.app import broker
from workers.entites import ExtracMessage


class FileService:
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
            await db.session.commit()
            await broker.publish(
                message=ExtracMessage(kb_file_id=kb_file_id, metadata={}).model_dump(),
                topic=settings.EXTRACTOR_TOPIC,
            )
            return True
        except Exception as e:
            logger.exception("上传文件失败")
            await db.session.rollback()
            raise CustomException(message=f"创建文件失败: {str(e)}") from None
