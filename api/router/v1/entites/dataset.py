from pydantic import BaseModel


class CreateDatasetRequest(BaseModel):
    name: str
    description: str
    files: list[str]
    embedding_model: str
    embedding_provider: str
