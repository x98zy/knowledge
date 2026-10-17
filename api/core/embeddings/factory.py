from common.entites import EmbeddingConfig, ModelProvider
from core.embeddings.base import l2_normalize, l2_normalize_batch
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
        # 统一在出口做 L2 归一化：检索查询向量与入库文档向量必须走同一处理，
        # IP 内积度量才能等价于余弦相似度
        return l2_normalize(await self.embedding_model.embed(text))

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = await self.embedding_model.batch_embed(texts)
        return l2_normalize_batch(embeddings)
