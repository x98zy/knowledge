from typing import Literal

from pydantic import BaseModel, Field


class CreateKnowledgeFileRequest(BaseModel):
    dataset_id: str
    file_key: str
    enable_semantic: bool = Field(
        default=False, description="是否开启智能分段，开启后由大模型进行语义分割，分段规则可省略"
    )

    # 以下分段规则字段在 enable_semantic=True 时可全部省略，省略后用默认值落库 ProcessRule
    # （extract worker 依赖 ProcessRule 记录才能执行，因此不能为 None，只能给默认）
    segment_mode: Literal["text_model", "qa_model", "hierarchical_model", "semantic_model"] = Field(
        default="text_model", description="分段模式: text_model;qa_model;hierarchical_model;semantic_model"
    )
    pre_rule: str = Field(
        default="remove_extra_spaces", description="预处理规则 1.remove_urls_emails 2.remove_extra_spaces"
    )
    max_tokens: int = Field(default=500, description="分段最大长度")
    overlap: int = Field(default=50, description="分段重叠长度")
    delimiter: str = Field(default="\\n\\n", description="分段分隔符")

    parent_mode: str | None = Field(default=None, description="父分段规则")
    child_delimiter: str | None = Field(default=None, description="子分段分隔符")
    child_overlap: int | None = Field(default=None, description="子分段重叠长度")
    child_max_tokens: int | None = Field(default=None, description="子分段最大长度")


class KnowledgeFileListRequest(BaseModel):
    page: int = 1
    page_size: int = 10
    keyword: str | None = None
