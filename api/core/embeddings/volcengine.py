from openai import AsyncOpenAI

from common.entites import EmbeddingConfig
from core.embeddings.base import EmbeddingModelBase


class VolcengineEmbeddingModel(EmbeddingModelBase):
    """基于火山引擎 Embedding 模型的实现类。

    通过 OpenAI Python SDK 兼容接口调用火山引擎 Embedding API。
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
        response = await self._client.embeddings.create(model=self._model, input=[text], encoding_format="float")
        return response.data[0].embedding

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        将多条文本批量编码为向量。

        Args:
            texts: 待编码的文本列表。

        Returns:
            与 texts 顺序一一对应的向量列表。
        """
        response = await self._client.embeddings.create(model=self._model, input=texts, encoding_format="float")
        # DashScope 返回的 data 列表按 input 顺序排列，直接提取 embedding 即可
        sorted_data = sorted(response.data, key=lambda x: x.index)
        embeddings = [item.embedding for item in sorted_data]
        return embeddings
