from datetime import datetime

from sqlalchemy import JSON, TEXT, BigInteger, Boolean, Column, String
from sqlalchemy.orm import Mapped

from models.base import BaseModel


class KbFile(BaseModel):
    __tablename__ = "kb_files"

    dataset_id: Mapped[str] = Column(String(255), nullable=False, comment="知识库ID", index=True)
    enable_semantic: Mapped[bool] = Column(
        Boolean, nullable=False, default=False, comment="是否开启语义分段, 开启后将由大模型进行语义分割"
    )
    file_name: Mapped[str] = Column(String(255), nullable=False, comment="文件名")
    file_key: Mapped[str] = Column(String(255), nullable=False, comment="文件OSS键名")
    status: Mapped[str] = Column(String(50), nullable=False, comment="文件处理状态", default="waiting")
    failed_reason: Mapped[str] = Column(TEXT, nullable=True, comment="文件处理失败原因")

    @property
    def dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "created_time": datetime.strftime(self.created_time, "%Y-%m-%d %H:%M:%S") if self.created_time else None,
            "updated_time": datetime.strftime(self.updated_time, "%Y-%m-%d %H:%M:%S") if self.updated_time else None,
            "status": self.status,
            "failed_reason": self.failed_reason,
        }


class FileSegments(BaseModel):
    __tablename__ = "file_segments"

    file_id: Mapped[str] = Column(String(255), nullable=False, comment="文件ID", index=True)
    dataset_id: Mapped[str] = Column(String(255), nullable=False, comment="知识库ID", index=True)
    content: Mapped[str] = Column(TEXT, nullable=False, comment="片段内容")
    answer: Mapped[str] = Column(TEXT, nullable=True, comment="片段答案")
    metadata_: Mapped[dict] = Column(JSON, nullable=False, comment="片段元数据")
    point_id: Mapped[str] = Column(String(255), nullable=True, comment="向量库id")
    status: Mapped[str] = Column(String(50), nullable=False, comment="片段处理状态", default="waiting")


class ChildSegment(BaseModel):
    __tablename__ = "child_segments"

    parent_id: Mapped[str] = Column(String(255), nullable=False, comment="父片段ID")
    dataset_id: Mapped[str] = Column(String(255), nullable=False, comment="知识库ID", index=True)
    file_id: Mapped[str] = Column(String(255), nullable=False, comment="文件ID", index=True)
    content: Mapped[str] = Column(TEXT, nullable=False, comment="片段内容")
    metadata_: Mapped[dict] = Column(JSON, nullable=False, comment="片段元数据")
    point_id: Mapped[str] = Column(String(255), nullable=True, comment="向量库id")
    status: Mapped[str] = Column(String(50), nullable=False, comment="片段处理状态", default="waiting")


class UploadFile(BaseModel):
    __tablename__ = "upload_files"

    file_name: Mapped[str] = Column(String(255), nullable=False, comment="文件名")
    file_hash: Mapped[str] = Column(String(255), nullable=False, comment="文件哈希值")
    file_key: Mapped[str] = Column(String(255), nullable=False, comment="文件OSS键名")
    file_size: Mapped[int] = Column(BigInteger, nullable=False, comment="文件大小")
    ext: Mapped[str] = Column(String(255), nullable=False, comment="文件扩展名")
