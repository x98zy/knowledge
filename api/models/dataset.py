from datetime import datetime

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped

from common.entites import PreProcessingRule, Rule, Segmentation, VectorProvider
from common.entites import ProcessRule as CProcessRule
from models.base import BaseModel


class Dataset(BaseModel):
    __tablename__ = "datasets"

    name: Mapped[str] = Column(String(255), unique=False, nullable=False, comment="知识库名称")
    description: Mapped[str] = Column(String(255), nullable=True, comment="知识库描述")
    logo: Mapped[str] = Column(String(255), nullable=False, comment="知识库logo图片地址")
    vector_type: Mapped[str] = Column(String(50), nullable=False, comment="向量库类型", default="milvus")
    collection_name: Mapped[str] = Column(String(255), nullable=False, comment="向量库集合名称")
    embedding_model: Mapped[str] = Column(String(255), nullable=False, comment="向量库嵌入模型")
    embedding_provider: Mapped[str] = Column(String(255), nullable=False, comment="向量库嵌入模型提供方")

    @property
    def provider(self) -> str:
        return VectorProvider(self.vector_type)

    @property
    def milvus_collection_name(self) -> str:
        return "Vector_Service" + self.collection_name.replace(" ", "_").replace("-", "_")

    @property
    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "embedding_model": self.embedding_model,
            "embedding_provider": self.embedding_provider,
            "created_time": datetime.strftime(self.created_time, "%Y-%m-%d %H:%M:%S") if self.created_time else None,
            "updated_time": datetime.strftime(self.updated_time, "%Y-%m-%d %H:%M:%S") if self.updated_time else None,
        }


class ProcessRule(BaseModel):
    __tablename__ = "process_rules"
    kb_file_id: Mapped[str] = Column(String(255), nullable=False, comment="文件ID", index=True)
    segment_mode: Mapped[str] = Column(String(50), nullable=False, comment="分段规则")
    pre_rule: Mapped[str] = Column(
        String(50), nullable=False, comment="预处理规则 1.remove_urls_emails 2.remove_extra_spaces"
    )
    max_tokens: Mapped[int] = Column(Integer, nullable=False, comment="分段最大长度")
    overlap: Mapped[int] = Column(Integer, nullable=False, comment="分段重叠长度")
    delimiter: Mapped[str] = Column(String(100), nullable=False, comment="分段分隔符")

    # 子分段模式
    parent_mode: Mapped[str] = Column(String(100), nullable=True, comment="父分段模式，只能是full-doc或者是paragraph")
    child_delimiter: Mapped[str] = Column(String(100), nullable=True, comment="子分段分隔符")
    child_max_tokens: Mapped[int] = Column(Integer, nullable=True, comment="子分段最大长度")
    child_overlap: Mapped[int] = Column(Integer, nullable=True, comment="子分段重叠长度")

    @property
    def tranform_rule(self) -> CProcessRule:
        pre_rules_list = []
        if self.pre_rule:
            pre_rules = self.pre_rule.split(";")
            for rule in pre_rules:
                pre_rules_list.append(PreProcessingRule(id=rule, enabled=True))
        return CProcessRule(
            mode="hierarchical" if self.segment_mode == "hierarchical_model" else "custom",
            rules=Rule(
                pre_processing_rules=pre_rules_list,
                segmentation=Segmentation(
                    separator=self.delimiter, max_tokens=self.max_tokens, chunk_overlap=self.overlap
                ),
            ),
            parent_mode=self.parent_mode,
            subchunk_segmentation=Segmentation(
                separator=self.child_delimiter, max_tokens=self.child_max_tokens, chunk_overlap=self.child_overlap
            )
            if self.parent_mode
            else None,
        )
