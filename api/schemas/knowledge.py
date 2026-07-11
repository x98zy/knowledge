from pydantic import BaseModel


class EmbeddingModel(BaseModel):
    """embedding model."""

    model: str
    provider: str


class EmbeddingListResponse(BaseModel):
    """embedding  model list success response body."""

    models: list[EmbeddingModel]
