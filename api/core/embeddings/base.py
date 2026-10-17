from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np

_EPS = 1e-12


def l2_normalize(vector: Sequence[float]) -> list[float]:
    """L2 归一化：返回单位向量，使向量 L2 模长为 1。

    Milvus dense 字段使用 IP（内积）度量，归一化后内积等价于余弦相似度，
    分数落在 [-1, 1]，排序不再受文档向量自身模长（文本长度/模型输出幅度）影响。
    写入向量与查询向量必须同时归一化，否则相似度仍会失真。

    Args:
        vector: 原始 embedding 向量。

    Returns:
        归一化后的单位向量；全零向量原样返回，避免除零放大噪声。
    """
    arr = np.asarray(vector, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm < _EPS:
        return arr.tolist()
    return (arr / norm).tolist()


def l2_normalize_batch(vectors: Sequence[Sequence[float]]) -> list[list[float]]:
    """批量 L2 归一化（矩阵化计算，供 batch_embed 使用）。

    逐行除以该行的 L2 模长；全零行的模长按 _EPS 兜底，结果仍为全零行。
    """
    arr = np.asarray(vectors, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"l2_normalize_batch 要求二维向量矩阵，实际维度: {arr.ndim}")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    # np.maximum：零向量行除以 _EPS，分子为 0 结果仍是全零，不产生 NaN
    return (arr / np.maximum(norms, _EPS)).tolist()


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
