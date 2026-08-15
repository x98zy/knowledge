from pydantic import BaseModel, Field

from common.entites import Document


class ExtracMessage(BaseModel):
    kb_file_id: str = Field(..., description="知识文件ID")
    metadata: dict = Field(default_factory=dict, description="文件元数据")


class EmbedMessage(BaseModel):
    documents: list[Document] = Field(..., description="待嵌入的文档列表")
    kb_file_id: str = Field(..., description="知识文件ID")
