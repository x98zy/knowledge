# api/models/outbox.py
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import Mapped

from models.base import BaseModel


class OutboxMessage(BaseModel):
    """Transactional Outbox 消息表，与业务数据同事务写入,保证消息的一致性"""

    __tablename__ = "outbox_messages"

    topic: Mapped[str] = Column(String(100), nullable=False, index=True, comment="Kafka topic")
    payload: Mapped[dict] = Column(JSON, nullable=False, comment="消息 JSON")
    status: Mapped[str] = Column(
        String(20), nullable=False, default="pending", index=True, comment="pending|sent|failed"
    )
    retry_count: Mapped[int] = Column(Integer, nullable=False, default=0, comment="重试次数")
    next_retry_at: Mapped[datetime] = Column(DateTime, nullable=True, comment="下次重试时间")
