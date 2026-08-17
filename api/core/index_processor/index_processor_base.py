"""Abstract interface for document loader implementations."""

from abc import ABC, abstractmethod

from common.entites import Document, ExtractSetting
from config.settings import settings
from core.model_manager import ModelInstance
from core.splitter.fixed_text_splitter import (
    EnhanceRecursiveCharacterTextSplitter,
    FixedRecursiveCharacterTextSplitter,
)
from core.splitter.text_splitter import TextSplitter
from models.dataset import Dataset


class BaseIndexProcessor(ABC):
    """Interface for extract files."""

    @abstractmethod
    def extract(self, extract_setting: ExtractSetting, **kwargs) -> list[Document]:
        raise NotImplementedError

    @abstractmethod
    def transform(self, documents: list[Document], **kwargs) -> list[Document]:
        raise NotImplementedError

    @abstractmethod
    def load(self, dataset: Dataset, documents: list[Document], with_keywords: bool = True, **kwargs) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def clean(self, dataset: Dataset, node_ids: list[str] | None, with_keywords: bool = True, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def retrieve(
        self,
        retrieval_method: str,
        query: str,
        dataset: Dataset,
        top_k: int,
        score_threshold: float,
        reranking_model: dict,
    ) -> list[Document]:
        raise NotImplementedError

    def _get_splitter(
        self,
        processing_rule_mode: str,
        max_tokens: int,
        chunk_overlap: int,
        separator: str,
        embedding_model_instance: ModelInstance | None,
    ) -> TextSplitter:
        """
        Get the NodeParser object according to the processing rule.
        """
        if processing_rule_mode in ["custom", "hierarchical"]:
            # The user-defined segmentation rule
            max_segmentation_tokens_length = settings.INDEXING_MAX_SEGMENTATION_TOKENS_LENGTH
            if max_tokens < 50 or max_tokens > max_segmentation_tokens_length:
                raise ValueError(f"Custom segment length should be between 50 and {max_segmentation_tokens_length}.")

            if separator:
                separator = separator.replace("\\n", "\n")

            character_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
                chunk_size=max_tokens,
                chunk_overlap=chunk_overlap,
                fixed_separator=separator,
                separators=["\n\n", "。", ". ", " ", ""],
                embedding_model_instance=embedding_model_instance,
            )
        else:
            # Automatic segmentation
            AUTOMATIC_RULES = {  # noqa: N806
                "pre_processing_rules": [
                    {"id": "remove_extra_spaces", "enabled": True},
                    {"id": "remove_urls_emails", "enabled": False},
                ],
                "segmentation": {"delimiter": "\n", "max_tokens": 500, "chunk_overlap": 50},
            }
            character_splitter = EnhanceRecursiveCharacterTextSplitter.from_encoder(
                chunk_size=AUTOMATIC_RULES["segmentation"]["max_tokens"],
                chunk_overlap=AUTOMATIC_RULES["segmentation"]["chunk_overlap"],
                separators=["\n\n", "。", ". ", " ", ""],
                embedding_model_instance=embedding_model_instance,
            )

        return character_splitter  # type: ignore
