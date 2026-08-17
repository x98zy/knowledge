"""Paragraph index processor."""

import uuid

from common.entites import Document, ExtractSetting, Rule
from core.cleaner.clean_processor import CleanProcessor
from core.extractor.extract_processor import ExtractProcessor
from core.index_processor.index_processor_base import BaseIndexProcessor
from core.vectordb.factory import VectorFactory
from models.dataset import Dataset
from utils.helper import generate_text_hash
from utils.text_process_utils import remove_leading_symbols


class ParagraphIndexProcessor(BaseIndexProcessor):
    async def extract(self, extract_setting: ExtractSetting, **kwargs) -> list[Document]:
        text_docs = await ExtractProcessor.extract(
            extract_setting=extract_setting,
            is_automatic=(
                kwargs.get("process_rule_mode") == "automatic" or kwargs.get("process_rule_mode") == "hierarchical"
            ),
        )

        return text_docs

    async def transform(self, documents: list[Document], **kwargs) -> list[Document]:
        process_rule = kwargs.get("process_rule")
        if not process_rule:
            raise ValueError("No process rule found.")
        if process_rule.get("mode") == "automatic":
            automatic_rule = {
                "pre_processing_rules": [
                    {"id": "remove_extra_spaces", "enabled": True},
                    {"id": "remove_urls_emails", "enabled": False},
                ],
                "segmentation": {"delimiter": "\n", "max_tokens": 500, "chunk_overlap": 50},
            }
            rules = Rule(**automatic_rule)
        else:
            if not process_rule.get("rules"):
                raise ValueError("No rules found in process rule.")
            rules = Rule(**process_rule.get("rules"))
        # Split the text documents into nodes.
        if not rules.segmentation:
            raise ValueError("No segmentation found in rules.")
        splitter = self._get_splitter(
            processing_rule_mode=process_rule.get("mode"),
            max_tokens=rules.segmentation.max_tokens,
            chunk_overlap=rules.segmentation.chunk_overlap,
            separator=rules.segmentation.separator,
            embedding_model_instance=kwargs.get("embedding_model_instance"),
        )
        all_documents = []
        for document in documents:
            # document clean
            document_text = CleanProcessor.clean(document.page_content, kwargs.get("process_rule", {}))
            document.page_content = document_text
            # parse document to nodes
            document_nodes = splitter.split_documents([document])
            split_documents = []
            for document_node in document_nodes:
                if document_node.page_content.strip():
                    doc_id = str(uuid.uuid4())
                    hash = generate_text_hash(document_node.page_content)
                    if document_node.metadata is not None:
                        document_node.metadata["doc_id"] = doc_id
                        document_node.metadata["doc_hash"] = hash
                    # delete Splitter character
                    page_content = remove_leading_symbols(document_node.page_content).strip()
                    if len(page_content) > 0:
                        document_node.page_content = page_content
                        split_documents.append(document_node)
            all_documents.extend(split_documents)
        return all_documents

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
