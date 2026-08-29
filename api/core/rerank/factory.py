from common.entites import ModelConfig, ModelProvider, SearchDocument
from core.rerank.tongyi import TongYiRerank
from core.rerank.volcengine import VolcengineRerankModel


class RerankFactory:
    def __init__(self, model_config: ModelConfig) -> None:
        self.model_config = model_config
        if model_config.provider == ModelProvider.TONGYI:
            self.rerank_model = TongYiRerank(
                base_url=model_config.config.get("base_url"),
                api_key=model_config.config.get("api_key"),
                model_name=model_config.name,
            )
        elif model_config.provider == ModelProvider.VOLCENGINE:
            self.rerank_model = VolcengineRerankModel(
                base_url=model_config.config.get("base_url"),
                api_key=model_config.config.get("api_key"),
                model_name=model_config.name,
            )
        else:
            raise ValueError("not supported rerank model")

    async def rerank(self, query: str, top_k: int, docs: list[SearchDocument], score: float) -> list[SearchDocument]:
        rerank_docs = await self.rerank_model.rerank(query, top_k, docs)
        docs = []
        for rerank_doc in rerank_docs:
            if rerank_doc.rerank_score >= score:
                docs.append(rerank_doc)
        return docs
