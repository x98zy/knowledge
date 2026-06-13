from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase
from uuid_extensions import uuid7


class BaseModel(DeclarativeBase):
    """基础模型类，包含审计字段，所有模型继承此类"""

    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid7.create()), comment="主键ID")

    # 软删除标记: 0-未删除, 1-已删除
    deleted = Column(Integer, default=0, nullable=False, comment="是否删除")

    # 审计字段
    created_time = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_time = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="修改时间",
    )
    created_by = Column(String(64), default="", nullable=False, comment="创建者")
    updated_by = Column(String(64), default="", nullable=False, comment="修改者")
