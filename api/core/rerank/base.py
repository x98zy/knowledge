from abc import ABC, abstractmethod

from common.entites import SearchDocument


class RerankModelBase(ABC):
    @abstractmethod
    async def rerank(self, query: str, top_k: int, docs: list[SearchDocument]) -> list[SearchDocument]:
        raise NotImplementedError
