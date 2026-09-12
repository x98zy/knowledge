"""StructuredProcessor index processor."""

import logging
import uuid

from common.entites import Document, ExtractSetting
from core.cleaner.clean_processor import CleanProcessor
from core.extractor.extract_processor import ExtractProcessor
from core.index_processor.index_processor_base import BaseIndexProcessor
from core.vectordb.factory import VectorFactory
from models.dataset import Dataset
from utils.helper import generate_text_hash
from utils.text_process_utils import remove_leading_symbols

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
        pass

    def _clean_and_split(self, documents: list[Document], splitter, process_rule) -> list[Document]:
        all_documents = []
        for document in documents:
            # document clean
            document_text = CleanProcessor.clean(document.page_content, process_rule)
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
