import json
import os
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.entites import ModelConfig
from config.path_config import ENV_DIR


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
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=24 * 60, description="Access token expiry in minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry in days")

    MILVUS_HOST: str = Field(..., description="MILVUS host地址")
    MILVUS_PORT: int = Field(description="MILVUS 端口", default=19530)
    MILVUS_USERNAME: str = Field(default="", description="MILVUS 用户名")
    MILVUS_PASSWORD: str = Field(default="", description="MILVUS 密码")
    MILVUS_DB: str = Field(default="knowledge", description="MILVUS 数据库名称")

    # 模型配置列表, 从 env 中读取 JSON 字符串, 格式:
    # MODELS=[{"type":"embedding","provider":"dashscope","name":"text-embedding-v3","config":"base64编码的JSON"}]
    MODELS: list[ModelConfig] = Field(default_factory=list, description="模型配置列表")

    ALIYUN_OSS_ACCESS_KEY: str = Field(..., description="阿里云 OSS 访问密钥")
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = Field(..., description="阿里云 OSS 访问密钥")
    ALIYUN_OSS_BUCKET: str = Field(..., description="阿里云 OSS 桶名")
    ALIYUN_OSS_REGION: str = Field(..., description="阿里云 OSS 区域")
    ALIYUN_OSS_ENDPOINT: str = Field(..., description="阿里云 OSS 端点")
    INDEXING_MAX_SEGMENTATION_TOKENS_LENGTH: int = Field(description="索引最大分段 token 长度", default=4000)
    CHILD_CHUNKS_PREVIEW_NUMBER: int = Field(description="子文档预览数量", default=50)
    QA_MODEL_NAME: str = Field(..., description="Q-A问答模型名称")

    @model_validator(mode="before")
    @classmethod
    def parse_models_json(cls, data: dict) -> dict:
        """将 env 中的 MODELS JSON 字符串解析为 list[ModelConfig]"""
        models_raw = data.get("MODELS")
        if isinstance(models_raw, str):
            models_raw = models_raw.strip()
            if models_raw:
                data["MODELS"] = json.loads(models_raw)
            else:
                data["MODELS"] = []
        return data

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
            "swagger_ui_parameters": {
                "persistAuthorization": True,  # 刷新页面后保留 Token
            },
        }

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        return (
            f"redis://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )

    @property
    def MILVUS_URL(self) -> str:  # noqa: N802
        return f"https://{self.MILVUS_HOST}:{self.MILVUS_PORT}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取全局 Settings 单例（lru_cache 缓存）。

    返回:
    - Settings: 配置实例。
    """
    return Settings()


settings = get_settings()
