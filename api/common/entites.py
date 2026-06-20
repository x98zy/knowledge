import base64
import json
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ChildDocument(BaseModel):
    """Class for storing a piece of text and associated metadata."""

    page_content: str

    vector: list[float] | None = None

    """Arbitrary metadata about the page content (e.g., source, relationships to other
        documents, etc.).
    """
    metadata: dict = Field(default_factory=dict)


class Document(BaseModel):
    page_content: str = Field(description="文档内容")
    metadata: dict = Field(default_factory=dict, description="文档元数据")
    score: float = Field(default=0.0, description="文档相似度分数")
    vector: list[float] | None = None
    children: list[ChildDocument] = Field(default_factory=list, description="子文档列表")


class ProcessMode(str, Enum):
    PARAGRAPH = "paragraph"
    QA = "qa"
    PARENT_CHILD = "parent_child"


class PreRule(str, Enum):
    REMOVE_EMAIL = "remove_email"
    REMOVE_URL = "remove_url"


class VectorProvider(str, Enum):
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


class ModelType(str, Enum):
    EMBEDDING = "embedding"
    LLM = "llm"
    OCR = "ocr"


class ModelConfig(BaseModel):
    """单条模型配置"""

    type: ModelType = Field(description="模型类型: embedding / llm / ocr")
    provider: str = Field(description="模型供应商, 如 dashscope / openai")
    name: str = Field(description="模型名称, 如 text-embedding-v3")
    config: dict = Field(default_factory=dict, description="模型专属配置(base64 解码后的 JSON)")

    @model_validator(mode="before")
    @classmethod
    def parse_config(cls, data: dict) -> dict:
        """将 config 字段从 base64 解码为 JSON"""
        if data.get("config"):
            data["config"] = json.loads(base64.b64decode(data["config"]).decode("utf-8"))
        return data
