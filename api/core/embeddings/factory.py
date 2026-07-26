from common.entites import EmbeddingConfig, ModelProvider
from core.embeddings.tongyi import TongyiEmbeddingModel
from core.embeddings.volcengine import VolcengineEmbeddingModel


class EmbeddingFactory:
    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        if config.provider == ModelProvider.TONGYI.value:
            self.embedding_model = TongyiEmbeddingModel(config)
        elif config.provider == ModelProvider.VOLCENGINE.value:
            self.embedding_model = VolcengineEmbeddingModel(config)
        else:
            raise ValueError(f"Unsupported model provider: {config.provider}")

    async def embed(self, text: str) -> list[float]:
        return await self.embedding_model.embed(text)

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        return await self.embedding_model.batch_embed(texts)
