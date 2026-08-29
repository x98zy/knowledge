from openai import AsyncOpenAI

from common.entites import SearchDocument
from core.rerank.base import RerankModelBase


class TongYiRerank(RerankModelBase):
    def __init__(self, base_url: str, api_key: str, model_name: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model_name = model_name

        self.client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    async def rerank(self, query: str, top_k: int, docs: list[SearchDocument]) -> list[SearchDocument]:
        documents = []
        for doc in docs:
            documents.append(doc.page_content)
        top_k = min(len(docs), top_k)
        rerank_results = await self.client.post(
            "/reranks",
            body={
                "model": self._model_name,
                "query": query,
                "documents": documents,
                "top_n": top_k,
            },
            cast_to=object,
        )
        ret = []
        for rerank_item in rerank_results.get("results", []):
            index = rerank_item.get("index")
            doc = docs[index]
            doc.rerank_score = rerank_item.get("relevance_score", 0.0)
            ret.append(doc)
        return ret
