"""StructuredProcessor index processor."""

import json
import logging

from common.entites import Document, ExtractSetting
from core.extractor.extract_processor import ExtractProcessor
from core.index_processor.index_processor_base import BaseIndexProcessor
from core.llm_generator.llm_generator import LLMGenerator
from core.vectordb.factory import VectorFactory
from models.dataset import Dataset

logger = logging.getLogger(__name__)


class StructuredProcessor(BaseIndexProcessor):
    async def extract(self, extract_setting: ExtractSetting, **kwargs) -> list[Document]:
        text_docs = await ExtractProcessor.extract(
            extract_setting=extract_setting,
            is_automatic=(
                kwargs.get("process_rule_mode") == "automatic" or kwargs.get("process_rule_mode") == "hierarchical"
            ),
        )
        return text_docs

    async def transform(self, documents: list[Document], **kwargs) -> list[Document]:
        llm_generator = LLMGenerator()
        all_documents = []
        for document in documents:
            llm_resp = await llm_generator.split_file_content(document.page_content)
            paragraphs = self.get_paragraphs_from_llm_response(llm_resp)
            for paragraph in paragraphs:
                # Create new documents for each paragraph
                new_document = Document(page_content=paragraph, metadata=document.metadata.copy())
                all_documents.append(new_document)
        return all_documents

    def get_paragraphs_from_llm_response(self, llm_resp: str) -> list[str]:
        try:
            resp_json = json.loads(llm_resp)
            if "result" in resp_json and isinstance(resp_json["result"], list):
                return resp_json["result"]
            else:
                logger.error("Invalid LLM response format: %s", llm_resp)
                return []
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s, error: %s", llm_resp, str(e))
            return []

    async def load(
        self, dataset: Dataset, documents: list[Document], with_keywords: bool = True, **kwargs
    ) -> list[str]:
        vector = VectorFactory(dataset)
        return await vector.create(documents)

    def clean(self, dataset: Dataset, node_ids: list[str] | None, with_keywords: bool = True, **kwargs):
        pass

    def retrieve(
        self,
        retrieval_method: str,
        query: str,
        dataset: Dataset,
        top_k: int,
        score_threshold: float,
        reranking_model: dict,
    ) -> list[Document]:
        # Set search parameters.
        pass
