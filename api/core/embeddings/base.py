from abc import ABC, abstractmethod


class EmbeddingModelBase(ABC):
    """Embedding 模型基类，定义统一的向量获取接口"""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        将单条文本编码为向量。

        Args:
            text: 待编码的文本。

        Returns:
            文本对应的向量表示（浮点数列表）。
        """

    @abstractmethod
    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        将多条文本批量编码为向量。

        Args:
            texts: 待编码的文本列表。

        Returns:
            与 texts 顺序一一对应的向量列表，即结果[i] 对应 texts[i] 的向量。
        """
