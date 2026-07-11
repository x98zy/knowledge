from pydantic import BaseModel


class CreateDatasetRequest(BaseModel):
    name: str
    description: str
    embedding_model: str
    embedding_provider: str


class KnowledgeListRequest(BaseModel):
    page: int = 1
    page_size: int = 10
    keyword: str | None = None
