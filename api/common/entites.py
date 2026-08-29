import base64
import json
from enum import Enum, StrEnum, auto
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class UploadFile(BaseModel):
    file_key: str = Field(description="OSS文件键")


class ChildDocument(BaseModel):
    """Class for storing a piece of text and associated metadata."""

    id: str | None = None

    page_content: str

    vector: list[float] | None = None

    """Arbitrary metadata about the page content (e.g., source, relationships to other
        documents, etc.).
    """
    metadata: dict = Field(default_factory=dict)


class Document(BaseModel):
    """Class for storing a piece of text and associated metadata."""

    id: str | None = None

    page_content: str

    vector: list[float] | None = None

    """Arbitrary metadata about the page content (e.g., source, relationships to other
        documents, etc.).
    """
    metadata: dict = Field(default_factory=dict)

    provider: str | None = "dify"

    children: list[ChildDocument] | None = None


class SearchDocument(BaseModel):
    id: str | None = None

    page_content: str

    metadata: dict = Field(default_factory=dict)
    score: float
    rerank_score: float | None = None


class ProcessMode(str, Enum):  # noqa: UP042
    PARAGRAPH = "paragraph"
    QA = "qa"
    PARENT_CHILD = "parent_child"


class PreRule(str, Enum):  # noqa: UP042
    REMOVE_EMAIL = "remove_email"
    REMOVE_URL = "remove_url"


class VectorProvider(str, Enum):  # noqa: UP042
    MILVUS = "milvus"
    CHROMA = "chroma"


class MilvusConfig(BaseModel):
    url: str = Field(description="Milvus数据库URL")
    username: str = Field(description="Milvus数据库用户名")
    password: str = Field(description="Milvus数据库密码")
    collection_name: str = Field(description="Milvus集合名称")
    embedding_model: str = Field(description="Milvus嵌入模型")
    embedding_provider: str = Field(description="Milvus嵌入模型提供方")
    milvus_db: str = Field(description="Milvus数据库名称")


class ModelType(str, Enum):  # noqa: UP042
    EMBEDDING = "embedding"
    LLM = "llm"
    OCR = "ocr"
    RERRANK = "rerank"

    @classmethod
    def value_of(cls, model_type: str) -> "ModelType":
        for model in cls:
            if model.value == model_type:
                return model
        raise ValueError(f"Model type {model_type} not found")


class ModelProvider(StrEnum):
    OPENAI = auto()
    TONGYI = auto()
    DASHSCOPE = auto()
    VOLCENGINE = auto()

    @classmethod
    def value_of(cls, provider_name: str) -> "ModelProvider":
        for provider in cls:
            if provider.value == provider_name:
                return provider
        raise ValueError(f"Model provider {provider_name} not found")


class ModelConfig(BaseModel):
    """单条模型配置"""

    type: ModelType = Field(description="模型类型: embedding / llm / ocr")
    provider: ModelProvider = Field(description="模型供应商, 如 dashscope / openai")
    name: str = Field(description="模型名称, 如 text-embedding-v3")
    config: dict = Field(default_factory=dict, description="模型专属配置(base64 解码后的 JSON)")

    @model_validator(mode="before")
    @classmethod
    def parse_config(cls, data: dict) -> dict:
        """将 config 字段从 base64 解码为 JSON"""
        if data.get("config"):
            data["config"] = json.loads(base64.b64decode(data["config"]).decode("utf-8"))
        return data


class EmbeddingConfig(BaseModel):
    """嵌入模型配置"""

    model: str = Field(description="嵌入模型名称")
    provider: str = Field(description="嵌入模型供应商方")
    api_key: str = Field(description="API密钥")
    base_url: str = Field(description="API基础URL")


class AuthHeader(BaseModel):
    authorization: str = Field(description="Authorization 头")


class ExtractSetting(BaseModel):
    """
    Model class for provider response.
    """

    upload_file: UploadFile | None = None

    def __init__(self, **data):
        super().__init__(**data)


class PreProcessingRule(BaseModel):
    id: str
    enabled: bool


class Segmentation(BaseModel):
    separator: str = "\n"
    max_tokens: int
    chunk_overlap: int = 0


class Rule(BaseModel):
    pre_processing_rules: list[PreProcessingRule] | None = None
    segmentation: Segmentation | None = None
    parent_mode: Literal["full-doc", "paragraph"] | None = None
    subchunk_segmentation: Segmentation | None = None


class ProcessRule(BaseModel):
    mode: Literal["automatic", "custom", "hierarchical"]
    rules: Rule | None = None


class ParentMode(StrEnum):
    FULL_DOC = "full-doc"
    PARAGRAPH = "paragraph"
