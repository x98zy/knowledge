from sqlalchemy import JSON, TEXT, BigInteger, Boolean, Column, String
from sqlalchemy.orm import Mapped

from models.base import BaseModel


class KbFile(BaseModel):
    __tablename__ = "kb_files"

    dataset_id: Mapped[str] = Column(String(255), nullable=False, comment="知识库ID", index=True)
    enable_semantic: Mapped[bool] = Column(
        Boolean, nullable=False, default=False, comment="是否开启语义分段, 开启后将由大模型进行语义分割"
    )
    file_key: Mapped[str] = Column(String(255), nullable=False, comment="文件OSS键名")


class FileSegments(BaseModel):
    __tablename__ = "file_segments"

    file_id: Mapped[str] = Column(String(255), nullable=False, comment="文件ID", index=True)
    dataset_id: Mapped[str] = Column(String(255), nullable=False, comment="知识库ID", index=True)
    content: Mapped[str] = Column(TEXT, nullable=False, comment="片段内容")
    answer: Mapped[str] = Column(TEXT, nullable=False, comment="片段答案")
    metadata_: Mapped[dict] = Column(JSON, nullable=False, comment="片段元数据")
    point_id: Mapped[str] = Column(String(255), nullable=False, comment="向量库id")


class ChildSegment(BaseModel):
    __tablename__ = "child_segments"

    parent_id: Mapped[str] = Column(String(255), nullable=False, comment="父片段ID")
    dataset_id: Mapped[str] = Column(String(255), nullable=False, comment="知识库ID", index=True)
    file_id: Mapped[str] = Column(String(255), nullable=False, comment="文件ID", index=True)
    content: Mapped[str] = Column(TEXT, nullable=False, comment="片段内容")
    metadata_: Mapped[dict] = Column(JSON, nullable=False, comment="片段元数据")
    point_id: Mapped[str] = Column(String(255), nullable=False, comment="向量库id")


class UploadFile(BaseModel):
    __tablename__ = "upload_files"

    file_name: Mapped[str] = Column(String(255), nullable=False, comment="文件名")
    file_hash: Mapped[str] = Column(String(255), nullable=False, comment="文件哈希值")
    file_key: Mapped[str] = Column(String(255), nullable=False, comment="文件OSS键名")
    file_size: Mapped[int] = Column(BigInteger, nullable=False, comment="文件大小")
    ext: Mapped[str] = Column(String(255), nullable=False, comment="文件扩展名")
