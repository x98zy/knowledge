from openai import AsyncOpenAI

from common.entites import EmbeddingConfig
from core.embeddings.base import EmbeddingModelBase


class TongyiEmbeddingModel(EmbeddingModelBase):
    """基于阿里云通义千问 Embedding 模型的实现类。

    通过 OpenAI Python SDK 兼容接口调用 DashScope Embedding API。
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = config.model

    async def embed(self, text: str) -> list[float]:
        """
        将单条文本编码为向量。

        Args:
            text: 待编码的文本。

        Returns:
            文本对应的向量表示（浮点数列表）。
        """
        response = await self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        将多条文本批量编码为向量。

        Args:
            texts: 待编码的文本列表。

        Returns:
            与 texts 顺序一一对应的向量列表。
        """
        response = await self._client.embeddings.create(model=self._model, input=texts)
        # DashScope 返回的 data 列表按 input 顺序排列，直接提取 embedding 即可
        embeddings = [item.embedding for item in response.data]
        # 确保返回顺序与输入顺序一致（按 index 排序）
        embeddings.sort(key=lambda x: x.index)  # type: ignore[attr-defined]
        return [emb.embedding for emb in embeddings]  # type: ignore[attr-defined]
