from openai import AsyncOpenAI

from common.entites import SearchDocument
from core.rerank.base import RerankModelBase


class VolcengineRerankModel(RerankModelBase):
    def __init__(self, base_url: str, api_key: str, model_name: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model_name = model_name

        self.client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    async def rerank(self, query: str, top_k: int, docs: list[SearchDocument]) -> list[SearchDocument]:
        return docs
