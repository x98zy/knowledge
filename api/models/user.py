from sqlalchemy import Column, String
from sqlalchemy.orm import Mapped

from models.base import BaseModel


class User(BaseModel):
    """用户模型"""

    __tablename__ = "users"

    username: Mapped[str] = Column(String(50), unique=True, nullable=False, comment="用户名")
    email: Mapped[str] = Column(String(100), unique=True, nullable=False, comment="邮箱地址")
    password_hash: Mapped[str] = Column(String(128), nullable=False, comment="密码哈希值")
    salt: Mapped[str] = Column(String(32), nullable=False, comment="密码盐值")
    last_login_time: Mapped[str] = Column(String(50), nullable=True, comment="最后登录时间")
    avator_file_key: Mapped[str] = Column(String(100), nullable=True, comment="用户头像文件键")

    @property
    def dict(self) -> dict:
        """将模型转换为字典"""
        return {
            "user_id": self.id,
            "username": self.username,
            "email": self.email,
            "avator_file_key": self.avator_file_key,
            "last_login_time": self.last_login_time,
        }
