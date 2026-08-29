import hashlib
import os
import tempfile
from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select, update

from common.code import ResponseCode
from common.entites import ModelConfig, ModelType
from common.error import CustomException
from config.settings import settings
from core.utils.page import Page, PaginationInput, paginate
from extensions.ext_db import db
from extensions.ext_log import logger
from extensions.ext_storage import storage
from models.dataset import Dataset
from models.document import UploadFile as UploadFileModel
from models.outbox import OutboxMessage
from models.user import User
from workers.app import send_broker_message
from workers.entites import DeleteDatasetMessage


class KnowledgeService:
    """知识服务"""

    @classmethod
    async def delete_knowledge(cls, knowledge_id: str, user_id: str) -> tuple[bool, str | None]:
        try:
            query = select(Dataset).filter(Dataset.id == knowledge_id, Dataset.deleted == 0)
            dataset = await db.session.execute(query)
            dataset = dataset.scalars().first()
            if not dataset:
                return False, "知识库不存在"
            if dataset.created_by_id != user_id:
                return False, "您无权限删除此知识库"
            dataset_delete_query = (
                update(Dataset)
                .where(Dataset.id == knowledge_id, Dataset.deleted == 0)
                .values(deleted=int(datetime.now().timestamp()))
            )
            # 先删mysql 记录，再投递消息到kafka中进行进行向量库数据的删除
            await db.session.execute(dataset_delete_query)
            query = select(User).where(User.id == user_id)
            current_user = await db.session.execute(query)
            current_user = current_user.scalars().first()
            # 同事务写 outbox：消息意图落盘,最大可能保证消息被投递
            if settings.START_BROKER_OUTBOX:
                outbox_msg = OutboxMessage(
                    topic=settings.DELETE_DATASET_TOPIC,
                    payload=DeleteDatasetMessage(kb_id=knowledge_id).model_dump(),
                    created_by_id=user_id,
                    updated_by_id=user_id,
                    created_by=current_user.username,
                    updated_by=current_user.username,
                )
                db.session.add(outbox_msg)
            else:
                await send_broker_message(
                    message=DeleteDatasetMessage(kb_id=knowledge_id).model_dump(), topic=settings.DELETE_DATASET_TOPIC
                )
            await db.session.commit()
            return True, None
        except Exception:
            logger.exception("删除知识库失败")
            await db.session.rollback()
            return False, "知识库删除失败"

    @classmethod
    async def get_knowledge_list(
        cls, user_id: str, page: int, page_size: int, keyword: str | None = None
    ) -> Page[Dataset]:
        """获取知识库列表接口"""
        query = (
            select(Dataset).filter(Dataset.created_by_id == user_id, Dataset.deleted == 0).order_by(Dataset.id.desc())
        )
        if keyword:
            query = query.where(Dataset.name.contains(keyword) | Dataset.description.contains(keyword))
        page_info = await paginate(
            query,
            PaginationInput(page=page, page_size=page_size),
        )
        return page_info

    @classmethod
    async def create_knowledge(
        cls, name: str, description: str, embedding_model: str, embedding_provider: str, user_id: str
    ) -> Dataset:
        """创建知识库接口"""
        # 检查embedding 模型是否存在
        model = next(
            (
                model
                for model in settings.MODELS
                if model.name == embedding_model and model.provider == embedding_provider
            ),
            None,
        )
        if not model:
            raise CustomException(
                message=f"无效的嵌入模型 {embedding_model}",
                code=ResponseCode.EMBEDDING_MODEL_INVALID.code,
                status_code=400,
            )
        # 文件暂时检查，后面如果embedding的时候文件不存在自己会显示错误
        query = select(User).where(User.id == user_id)
        current_user = await db.session.execute(query)
        current_user = current_user.scalars().first()
        record = Dataset(
            name=name,
            description=description,
            embedding_model=embedding_model,
            embedding_provider=embedding_provider,
            created_by=current_user.username,
            updated_by=current_user.username,
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
            collection_name=str(uuid4()),
            logo="default_dataset.png",
        )
        db.session.add(record)
        await db.session.commit()
        return record

    @classmethod
    async def get_embedding_models(cls) -> list[ModelConfig]:
        """获取嵌入模型列表"""
        all_models = [model for model in settings.MODELS if model.type == ModelType.EMBEDDING]
        return all_models

    @classmethod
    async def upload_file(cls, file: UploadFile, user_id: str) -> UploadFileModel:
        suffix = os.path.splitext(file.filename)[-1] if file.filename and "." in file.filename else ""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)

        try:
            # 2. 计算哈希
            query = select(User).where(User.id == user_id)
            current_user = await db.session.execute(query)
            current_user = current_user.scalars().first()

            file_hash = hashlib.sha256(content).hexdigest()

            # 3. 生成 OSS 文件 Key
            ext = suffix.lstrip(".") if suffix else ""
            file_key = f"uploads/{uuid4().hex}.{ext}" if ext else f"uploads/{uuid4().hex}"

            # 4. 上传到 OSS
            await storage.put_object(file_name=tmp_path, file_key=file_key)

            # 5. 写入数据库
            record = UploadFileModel(
                file_name=file.filename or file_key,
                file_hash=file_hash,
                file_key=file_key,
                file_size=len(content),
                ext=ext,
                created_by=current_user.username,
                updated_by=current_user.username,
            )
            db.session.add(record)
            await db.session.flush()

            return record
        finally:
            # 6. 清理临时文件
            os.unlink(tmp_path)
