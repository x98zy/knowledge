from common.entites import Document

from .base import VectorBase


class ChromaVector(VectorBase):
    async def create(self, documents: list[Document]) -> list[str]:
        """创建文档向量, 返回向量ID"""
        raise NotImplementedError

    async def vector_search(self, query: str) -> list[Document]:
        """向量搜索"""
        raise NotImplementedError

    async def full_text_search(self, query: str) -> list[Document]:
        """全文本搜索"""
        raise NotImplementedError

    async def delete(self, document_ids: list[str]) -> None:
        """删除文档向量"""
        raise NotImplementedError

    async def drop_collection(self, collection_name: str) -> None:
        """删除向量集合"""
        raise NotImplementedError

    async def embedding(self, text: list[str]) -> list[list[float]]:
        """文本文本的向量表示"""
        raise NotImplementedError

    async def update_metadata(self, document_ids: list[str], metadata: dict) -> None:
        """更新文档元数据"""
        raise NotImplementedError

    async def update_content_by_id(self, document_id: str, content: str) -> None:
        """更新文档内容"""
        raise NotImplementedError
