"""Paragraph index processor."""

import logging
import re
import uuid

from common.async_pool import AsyncExecutorPool
from common.entites import Document, ExtractSetting, Rule
from core.cleaner.clean_processor import CleanProcessor
from core.extractor.extract_processor import ExtractProcessor
from core.index_processor.index_processor_base import BaseIndexProcessor
from core.llm_generator.llm_generator import LLMGenerator
from core.vectordb.factory import VectorFactory
from models.dataset import Dataset
from utils.helper import generate_text_hash
from utils.text_process_utils import remove_leading_symbols

logger = logging.getLogger(__name__)


class QAIndexProcessor(BaseIndexProcessor):
    async def extract(self, extract_setting: ExtractSetting, **kwargs) -> list[Document]:
        text_docs = await ExtractProcessor.extract(
            extract_setting=extract_setting,
            is_automatic=(
                kwargs.get("process_rule_mode") == "automatic" or kwargs.get("process_rule_mode") == "hierarchical"
            ),
        )
        return text_docs

    async def transform(self, documents: list[Document], **kwargs) -> list[Document]:
        preview = kwargs.get("preview")
        process_rule = kwargs.get("process_rule")
        if not process_rule:
            raise ValueError("No process rule found.")
        if not process_rule.get("rules"):
            raise ValueError("No rules found in process rule.")
        rules = Rule(**process_rule.get("rules"))
        splitter = self._get_splitter(
            processing_rule_mode=process_rule.get("mode"),
            max_tokens=rules.segmentation.max_tokens if rules.segmentation else 0,
            chunk_overlap=rules.segmentation.chunk_overlap if rules.segmentation else 0,
            separator=rules.segmentation.separator if rules.segmentation else "",
            embedding_model_instance=kwargs.get("embedding_model_instance"),
        )

        # Split the text documents into nodes.
        all_documents: list[Document] = []
        all_qa_documents: list[Document] = []
        for document in documents:
            # document clean
            document_text = CleanProcessor.clean(document.page_content, kwargs.get("process_rule") or {})
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
                    page_content = document_node.page_content
                    document_node.page_content = remove_leading_symbols(page_content)
                    split_documents.append(document_node)
            all_documents.extend(split_documents)
        if preview:
            await self._format_qa_document(
                all_documents[0],
                all_qa_documents,
                kwargs.get("doc_language", "English"),
            )
        else:
            async with AsyncExecutorPool(max_concurrency=20) as pool:
                for i in range(0, len(all_documents), 10):
                    sub_documents = all_documents[i : i + 10]
                    for doc in sub_documents:
                        pool.submit(
                            self._format_qa_document, doc, all_qa_documents, kwargs.get("doc_language", "English")
                        )
        return all_qa_documents

    async def load(self, dataset: Dataset, documents: list[Document], with_keywords: bool = True, **kwargs):
        vector = VectorFactory(dataset)
        await vector.create(documents)

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
    ):
        pass

    async def _format_qa_document(self, document_node, all_qa_documents, document_language):
        format_documents = []
        if document_node.page_content is None or not document_node.page_content.strip():
            return
        try:
            # qa model document
            response = await LLMGenerator().generate_qa_document(document_node.page_content, document_language)
            document_qa_list = self._format_split_text(response)
            qa_documents = []
            for result in document_qa_list:
                qa_document = Document(page_content=result["question"], metadata=document_node.metadata.copy())
                if qa_document.metadata is not None:
                    doc_id = str(uuid.uuid4())
                    hash = generate_text_hash(result["question"])
                    qa_document.metadata["answer"] = result["answer"]
                    qa_document.metadata["doc_id"] = doc_id
                    qa_document.metadata["doc_hash"] = hash
                qa_documents.append(qa_document)
            format_documents.extend(qa_documents)
        except Exception:
            logger.exception("Failed to format qa document")

        all_qa_documents.extend(format_documents)

    def _format_split_text(self, text):
        regex = r"Q\d+:\s*(.*?)\s*A\d+:\s*([\s\S]*?)(?=Q\d+:|$)"
        matches = re.findall(regex, text, re.UNICODE)

        return [{"question": q, "answer": re.sub(r"\n\s*", "\n", a.strip())} for q, a in matches if q and a]
