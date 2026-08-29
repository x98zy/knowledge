"""Paragraph index processor."""

import asyncio
import uuid

from common.entites import ChildDocument, Document, ExtractSetting, ParentMode, Rule
from config.settings import settings
from core.cleaner.clean_processor import CleanProcessor
from core.extractor.extract_processor import ExtractProcessor
from core.index_processor.index_processor_base import BaseIndexProcessor
from core.model_manager import ModelInstance
from core.vectordb.factory import VectorFactory
from models.dataset import Dataset
from utils.helper import generate_text_hash


class ParentChildIndexProcessor(BaseIndexProcessor):
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
        if not process_rule.get("rules"):
            raise ValueError("No rules found in process rule.")
        rules = Rule(**process_rule.get("rules"))
        all_documents: list[Document] = []
        if rules.parent_mode == ParentMode.PARAGRAPH:
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
            # 清洗与父子分段是 CPU 密集的同步操作，放线程池执行避免阻塞事件循环导致 Kafka 心跳超时
            return await asyncio.to_thread(
                self._clean_and_split_paragraph, documents, splitter, rules, process_rule, kwargs
            )
        elif rules.parent_mode == ParentMode.FULL_DOC:
            return await asyncio.to_thread(self._split_full_doc, documents, rules, process_rule, kwargs)

        return all_documents

    def _clean_and_split_paragraph(
        self, documents: list[Document], splitter, rules: Rule, process_rule: dict, kwargs: dict
    ) -> list[Document]:
        all_documents: list[Document] = []
        for document in documents:
            if kwargs.get("preview") and len(all_documents) >= 10:
                return all_documents
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
                    document_node.metadata["doc_id"] = doc_id
                    document_node.metadata["doc_hash"] = hash
                    # delete Splitter character
                    page_content = document_node.page_content
                    if page_content.startswith(".") or page_content.startswith("。"):
                        page_content = page_content[1:].strip()
                    else:
                        page_content = page_content
                    if len(page_content) > 0:
                        document_node.page_content = page_content
                        # parse document to child nodes
                        child_nodes = self._split_child_nodes(
                            document_node, rules, process_rule.get("mode"), kwargs.get("embedding_model_instance")
                        )
                        document_node.children = child_nodes
                        split_documents.append(document_node)
            all_documents.extend(split_documents)
        return all_documents

    def _split_full_doc(self, documents: list[Document], rules: Rule, process_rule: dict, kwargs: dict) -> list[Document]:
        page_content = "\n".join([document.page_content for document in documents])
        document = Document(page_content=page_content, metadata=documents[0].metadata)
        # parse document to child nodes
        child_nodes = self._split_child_nodes(
            document, rules, process_rule.get("mode"), kwargs.get("embedding_model_instance")
        )
        if kwargs.get("preview"):  # noqa: SIM102
            if len(child_nodes) > settings.CHILD_CHUNKS_PREVIEW_NUMBER:
                child_nodes = child_nodes[: settings.CHILD_CHUNKS_PREVIEW_NUMBER]

        document.children = child_nodes
        doc_id = str(uuid.uuid4())
        hash = generate_text_hash(document.page_content)
        document.metadata["doc_id"] = doc_id
        document.metadata["doc_hash"] = hash
        return [document]

    async def load(
        self, dataset: Dataset, documents: list[Document], with_keywords: bool = True, **kwargs
    ) -> list[str]:
        vector = VectorFactory(dataset)
        pks = []
        for document in documents:
            child_documents = document.children
            if child_documents:
                formatted_child_documents = [
                    Document(**child_document.model_dump()) for child_document in child_documents
                ]
                ids = await vector.create(formatted_child_documents)
                pks.extend(ids)
        return pks

    def clean(self, dataset: Dataset, node_ids: list[str] | None, with_keywords: bool = True, **kwargs):
        # node_ids is segment's node_ids
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
        pass

    def _split_child_nodes(
        self,
        document_node: Document,
        rules: Rule,
        process_rule_mode: str,
        embedding_model_instance: ModelInstance | None,
    ) -> list[ChildDocument]:
        if not rules.subchunk_segmentation:
            raise ValueError("No subchunk segmentation found in rules.")
        child_splitter = self._get_splitter(
            processing_rule_mode=process_rule_mode,
            max_tokens=rules.subchunk_segmentation.max_tokens,
            chunk_overlap=rules.subchunk_segmentation.chunk_overlap,
            separator=rules.subchunk_segmentation.separator,
            embedding_model_instance=embedding_model_instance,
        )
        # parse document to child nodes
        child_nodes = []
        child_documents = child_splitter.split_documents([document_node])
        for child_document_node in child_documents:
            if child_document_node.page_content.strip():
                doc_id = str(uuid.uuid4())
                hash = generate_text_hash(child_document_node.page_content)
                child_document = ChildDocument(
                    page_content=child_document_node.page_content, metadata=document_node.metadata
                )
                child_document.metadata["doc_id"] = doc_id
                child_document.metadata["doc_hash"] = hash
                child_page_content = child_document.page_content
                if child_page_content.startswith(".") or child_page_content.startswith("。"):
                    child_page_content = child_page_content[1:].strip()
                if len(child_page_content) > 0:
                    child_document.page_content = child_page_content
                    child_nodes.append(child_document)
        return child_nodes
