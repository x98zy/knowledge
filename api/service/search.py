import asyncio

from sqlalchemy import select

from common.entites import SearchDocument
from common.error import CustomException
from core.rerank.factory import RerankFactory
from core.vectordb.factory import VectorFactory
from extensions.ext_db import db
from models.dataset import Dataset
from service.model_service import ModelService


class SearchService:
    @classmethod
    async def vector_search(
        cls,
        dataset_ids: list[str],
        query: str,
        top_k: int,
        query_filter: dict,
        score: float,
        rerank_model: str | None = None,
        rerank_model_provider: str | None = None,
    ):
        dataset_query = select(Dataset).where(Dataset.id.in_(dataset_ids), Dataset.deleted == 0)
        result = await db.session.execute(dataset_query)
        datasets = result.scalars().all()
        if not datasets:
            raise CustomException("知识库不存在")
        search_docs = await asyncio.gather(
            *[VectorFactory(dataset).vector_search(query, top_k, score, query_filter) for dataset in datasets]
        )
        docs: list[SearchDocument] = []
        for doc_list in search_docs:
            docs.extend(doc_list)
        if rerank_model and rerank_model_provider:
            model_config = ModelService.get_model(rerank_model, rerank_model_provider)
            rerank_factory = RerankFactory(model_config)
            docs = await rerank_factory.rerank(query, top_k, docs, score)

        else:
            docs = sorted(docs, key=lambda obj: obj.score, reverse=True)
        return [doc.model_dump() for doc in docs]
