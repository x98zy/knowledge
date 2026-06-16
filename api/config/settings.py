import os
from functools import lru_cache

from api.config.path_config import ENV_DIR
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=f"{ENV_DIR}/.env.{os.getenv('ENV', 'dev')}", case_sensitive=True)

    MYSQL_HOST: str = Field(..., description="MYSQL host地址")
    MYSQL_PORT: int = Field(description="MYSQL 端口", default=3306)
    MYSQL_USER: str = Field(..., description="MYSQL 用户名")
    MYSQL_PASSWORD: str = Field(..., description="MYSQL 密码")
    MYSQL_DATABASE: str = Field(..., description="MYSQL 数据库名")
    MYSQL_POOL_SIZE: int = Field(description="MYSQL 连接池大小", default=100)
    MYSQL_MAX_OVERFLOW_SIZE: int = Field(description="MYSQL 最大溢出连接数", default=10)
    MYSQL_POOL_RECYCLE: int = Field(description="MYSQL 连接池回收时间", default=3600)

    REDIS_HOST: str = Field(..., description="REDIS host地址")
    REDIS_PORT: int = Field(description="REDIS 端口", default=6379)
    REDIS_PASSWORD: str = Field(..., description="REDIS 密码")
    REDIS_DB: int = Field(description="REDIS 数据库", default=0)
    REDIS_USERNAME: str = Field(default="", description="REDIS 用户名")

    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production-use-a-random-256-bit-key",
        description="JWT signing key. Use a random 256-bit key in production.",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry in minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry in days")

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        """构建数据库连接 URL"""
        return f"mysql+asyncmy://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def FASTAPI_CONFIG(self) -> dict:  # noqa: N802
        """返回 FastAPI 配置"""
        return {
            "docs_url": "/docs",
            "root_path": "/api/v1",
        }

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        return (
            f"redis://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取全局 Settings 单例（lru_cache 缓存）。

    返回:
    - Settings: 配置实例。
    """
    return Settings()


settings = get_settings()
