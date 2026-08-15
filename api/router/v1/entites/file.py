from typing import Literal

from pydantic import BaseModel, Field


class CreateKnowledgeFileRequest(BaseModel):
    dataset_id: str
    file_key: str
    enable_semantic: bool = False

    segment_mode: Literal["text_model", "qa_model", "hierarchical_model"] = Field(
        ..., description="分段模式: text_model;qa_model;hierarchical_model"
    )
    pre_rule: str = Field(..., description="预处理规则 1.remove_urls_emails 2.remove_extra_spaces")
    max_tokens: int = Field(..., description="分段最大长度")
    overlap: int = Field(..., description="分段重叠长度")
    delimiter: str = Field(..., description="分段分隔符")

    parent_mode: str | None = Field(default=None, description="父分段规则")
    child_delimiter: str | None = Field(default=None, description="子分段分隔符")
    child_overlap: int | None = Field(default=None, description="子分段重叠长度")
    child_max_tokens: int | None = Field(default=None, description="子分段最大长度")


class KnowledgeFileListRequest(BaseModel):
    page: int = 1
    page_size: int = 10
    keyword: str | None = None
