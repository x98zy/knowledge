from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="用户查询")
    top_k: int = Field(..., description="返回的top_k值")
    score: float = Field(..., description="分数阈值")
    query_filter: dict = Field(default_factory=dict, description="用户提问")
    dataset_ids: list[str] = Field(default=[], description="检索的知识库")
    rerank_model: str | None = Field(default=None, description="重排模型名称")
    rerank_model_provider: str | None = Field(default=None, description="重排模型供应商")
