from typing import Any

from pymilvus import AsyncMilvusClient
from pymilvus.milvus_client import IndexParams
from uuid_extensions import uuid7

from common.entites import Document, MilvusConfig, SearchDocument
from extensions.ext_log import logger
from extensions.ext_redis import redis_client

from .base import VectorBase
from .entites import VectorField


class MilvusVector(VectorBase):
    def __init__(self, config: MilvusConfig) -> None:
        self.config = config
        self.collection_name = config.collection_name
        self._consistency_level = "Session"  # Consistency level for Milvus operations
        self.client = AsyncMilvusClient(
            uri=config.url, username=config.username, password=config.password, db_name=config.milvus_db
        )
        self._fields: list[str] = []

    async def _load_collection_fields(self, fields: list[str] | None = None):
        if fields is None:
            # Load collection fields from remote server
            collection_info = await self.client.describe_collection(self.collection_name)
            fields = [field["name"] for field in collection_info["fields"]]
        # Since primary field is auto-id, no need to track it
        self._fields = [f for f in fields if f != VectorField.ID.value]

    async def create_collection(self, embeddings: list) -> None:
        """创建向量集合"""
        lock_name = f"vector_indexing_lock_{self.collection_name}"
        async with redis_client.lock(lock_name, timeout=20):
            collection_exist_cache_key = f"vector_indexing_{self.collection_name}"
            if await redis_client.get(collection_exist_cache_key):
                return
            if not await self.client.has_collection(self.collection_name):
                from pymilvus import CollectionSchema, DataType, FieldSchema, Function, FunctionType  # type: ignore
                from pymilvus.orm.types import infer_dtype_bydata

                dim = len(embeddings[0])
                fields = []
                fields.append(FieldSchema(VectorField.METADATA.value, DataType.JSON, max_length=65_535))
                # 全文检索在设置文本字段的时候需要开启分析器，分析器需要配置分词器和过滤器，将一段长文本拆分成多个词token, 用于后续的检索
                # 分词器只有一个，过滤器可以配置多个，例如stop_worlds去除停用词，stemmer对单词进行根词提取，lowercase对单词进行小写转换
                # 中文的分词器可以使用jieba分词器
                content_field_kwargs: dict[str, Any] = {
                    "max_length": 65_535,
                    "enable_analyzer": True,
                }
                # filters: ["cncharonly"] — 在分词之后应用过滤器，只保留中文字符，过滤掉数字、英文字母、标点符号等无关 token
                content_field_kwargs["analyzer_params"] = {
                    "tokenizer": "jieba",
                }
                fields.append(FieldSchema(VectorField.CONTENT.value, DataType.VARCHAR, **content_field_kwargs))
                fields.append(FieldSchema(VectorField.ID.value, DataType.VARCHAR, is_primary=True, max_length=50))
                fields.append(FieldSchema(VectorField.VECTOR.value, infer_dtype_bydata(embeddings[0]), dim=dim))
                fields.append(FieldSchema(VectorField.SPARSE_VECTOR.value, DataType.SPARSE_FLOAT_VECTOR))
                schema = CollectionSchema(fields)
                # 添加BM25函数，用于全文检索,当插入文本时，会自动调用该函数，将文本转换为BM25向量，用于后续的检索
                bm25_function = Function(
                    name="text_bm25_emb",
                    input_field_names=[VectorField.CONTENT.value],
                    output_field_names=[VectorField.SPARSE_VECTOR.value],
                    function_type=FunctionType.BM25,
                )
                schema.add_function(bm25_function)

                # 添加索引
                index_params = {"metric_type": "IP", "index_type": "HNSW", "params": {"M": 8, "efConstruction": 64}}
                index_params_obj = IndexParams()
                index_params_obj.add_index(field_name=VectorField.VECTOR.value, **index_params)
                index_params_obj.add_index(
                    field_name=VectorField.SPARSE_VECTOR.value, index_type="AUTOINDEX", metric_type="BM25"
                )
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    schema=schema,
                    index_params=index_params_obj,
                    consistency_level=self._consistency_level,
                )
            await redis_client.set(collection_exist_cache_key, 1, ex=3600)

    async def create(self, texts: list[Document], embeddings: list[list[float]], **kwargs) -> list[str]:
        """创建文档向量, 返回向量ID"""
        await self.create_collection(embeddings)
        return await self.add_texts(texts, embeddings)

    async def add_texts(self, documentss: list[Document], embeddings: list[list[float]]) -> list[str]:
        """
        Add texts and their embeddings to the collection.
        """
        insert_dict_list = []
        for i in range(len(documentss)):
            insert_dict = {
                # Do not need to insert the sparse_vector field separately, as the text_bm25_emb
                # function will automatically convert the native text into a sparse vector for us.
                VectorField.CONTENT.value: documentss[i].page_content,
                VectorField.VECTOR.value: embeddings[i],
                VectorField.METADATA.value: documentss[i].metadata,
                VectorField.ID.value: str(uuid7()),
            }
            insert_dict_list.append(insert_dict)
        # Total insert count
        total_count = len(insert_dict_list)
        pks: list[str] = []

        for i in range(0, total_count, 1000):
            # Insert into the collection.
            batch_insert_list = insert_dict_list[i : i + 1000]
            try:
                result = await self.client.insert(collection_name=self.collection_name, data=batch_insert_list)
                if len(batch_insert_list) != result.get("insert_count"):
                    raise RuntimeError("milvus 插入数据失败")
                pks.extend(result.get("ids", []))
            except Exception as e:
                logger.exception("Failed to insert batch starting at entity: %s/%s", i, total_count)
                raise e

        return pks

    def _process_search_result(self, results: list[dict], score: float) -> list[SearchDocument]:
        docs: list[SearchDocument] = []
        for hits in results:
            for hit in hits:
                # IP 度量下 distance 为相似度，越大越相关，低于阈值直接过滤
                if hit["distance"] < score:
                    continue
                entity = hit.get("entity", {})
                metadata = entity.get(VectorField.METADATA.value, {}) or {}
                metadata["score"] = hit["distance"]
                docs.append(
                    SearchDocument(
                        id=str(hit["id"]),
                        page_content=entity.get(VectorField.CONTENT.value, ""),
                        metadata=metadata,
                        score=hit["distance"],
                    )
                )
        return docs

    async def vector_search(
        self, query_embedding: list[float], top_k: int, score: float, query_filter: dict
    ) -> list[SearchDocument]:
        """向量搜索"""
        results = await self.client.search(
            collection_name=self.collection_name,
            # search 要求 data 为向量列表(list[list[float]])，单个查询向量也需包一层
            data=[query_embedding],
            limit=max(1, top_k),
            output_fields=[VectorField.ID.value, VectorField.CONTENT.value, VectorField.METADATA.value],
            anns_field=VectorField.VECTOR.value,
            search_params={"metric_type": "IP"},
        )
        return self._process_search_result(results, score)

    async def full_text_search(self, query: str) -> list[Document]:
        """全文本搜索"""
        raise NotImplementedError

    async def delete(self, document_ids: list[str]) -> None:
        """删除文档向量"""
        await self.client.delete(collection_name=self.collection_name, ids=document_ids, timeout=30)

    async def drop_collection(self) -> None:
        """删除向量集合"""
        await self.client.drop_collection(self.collection_name)

    async def embedding(self, text: list[str]) -> list[list[float]]:
        """文本文本的向量表示"""
        raise NotImplementedError

    async def update_metadata(self, document_ids: list[str], metadata: dict) -> None:
        """更新文档元数据"""
        raise NotImplementedError

    async def update_content_by_id(self, document_id: str, content: str) -> None:
        """更新文档内容"""
        raise NotImplementedError
