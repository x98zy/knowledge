import time

from common.entites import Document, EmbeddingConfig, MilvusConfig, SearchDocument, VectorProvider
from config.settings import settings
from core.embeddings.factory import EmbeddingFactory
from extensions.ext_log import logger
from models.dataset import Dataset
from service.model_service import ModelService

from .chroma import ChromaVector
from .milvus import MilvusVector


class VectorFactory:
    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
        if self.dataset.provider == VectorProvider.MILVUS:
            config = MilvusConfig(
                url=settings.MILVUS_URL,
                username=settings.MILVUS_USERNAME,
                password=settings.MILVUS_PASSWORD,
                collection_name=self.dataset.milvus_collection_name,
                embedding_model=self.dataset.embedding_model,
                embedding_provider=self.dataset.embedding_provider,
                milvus_db=settings.MILVUS_DB,
            )
            self.vector = MilvusVector(config)
        elif self.dataset.provider == VectorProvider.CHROMA:
            self.vector = ChromaVector()
        else:
            raise ValueError(f"不支持的向量库类型: {self.dataset.provider}")
        self.init_embedding_factory()

    def init_embedding_factory(self):
        model = ModelService.get_model(self.dataset.embedding_model, self.dataset.embedding_provider)
        config = EmbeddingConfig(
            provider=self.dataset.embedding_provider,
            model=self.dataset.embedding_model,
            api_key=model.config.get("api_key", ""),
            base_url=model.config.get("base_url", ""),
        )
        self.embedding_factory = EmbeddingFactory(config)

    async def create(self, documents: list[Document], **kwargs) -> list[str]:
        all_point_ids = []
        if documents:
            start = time.time()
            logger.info("start embedding %s texts %s", len(documents), start)
            batch_size = 10
            total_batches = len(documents) + batch_size - 1
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                batch_start = time.time()
                logger.info("Processing batch %s/%s (%s texts)", i // batch_size + 1, total_batches, len(batch))
                batch_embeddings = await self.embedding_factory.batch_embed(
                    [document.page_content for document in batch]
                )
                logger.info(
                    "Embedding batch %s/%s took %s s", i // batch_size + 1, total_batches, time.time() - batch_start
                )
                pks = await self.vector.create(texts=batch, embeddings=batch_embeddings, **kwargs)
                all_point_ids.extend(pks)
            logger.info("Embedding %s texts took %s s", len(documents), time.time() - start)
        return all_point_ids

    async def drop_collection(self, timeout: float | None = None):
        await self.vector.drop_collection(timeout=timeout)

    async def delete_by_ids(self, ids: list[str]):
        await self.vector.delete(ids)

    async def vector_search(self, query: str, top_k: int, score: float, query_filter: dict) -> list[SearchDocument]:
        query_embedding = await self.embedding_factory.embed(query)
        return await self.vector.vector_search(query_embedding, top_k, score, query_filter)

    async def full_text_search(self, query: str, top_k: int, score: float, query_filter: dict) -> list[SearchDocument]:
        return await self.vector.full_text_search(query, top_k, score, query_filter)

    async def hybrid_search(self, query: str, top_k: int, score: float, query_filter: dict) -> list[SearchDocument]:
        query_embedding = await self.embedding_factory.embed(query)
        return await self.vector.hybrid_search(query, query_embedding, top_k, score, query_filter)
