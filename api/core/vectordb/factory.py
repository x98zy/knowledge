from common.entites import MilvusConfig, VectorProvider
from config.settings import settings
from models.dataset import Dataset

from .chroma import ChromaVector
from .milvus import MilvusVector


class VectorFactory:
    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
        if self.dataset.provider == VectorProvider.MILVUS:
            config = MilvusConfig(
                url=settings.MILVUS_URL,
                username=settings.MILVUS_USERNAME,
                password=settings.MILVUS_PASSWORD,
                collection_name=self.dataset.milvus_collection_name,
                embedding_model=self.dataset.embedding_model,
                embedding_provider=self.dataset.embedding_provider,
                milvus_db=settings.MILVUS_DB,
            )
            self.vector = MilvusVector(config)
        elif self.dataset.provider == VectorProvider.CHROMA:
            self.vector = ChromaVector()
        else:
            raise ValueError(f"不支持的向量库类型: {self.dataset.provider}")
