from fastapi import APIRouter

from common.response import SuccessResponse
from service.search import SearchService

from .entites.search import SearchRequest

search_router = APIRouter(prefix="/search", tags=["搜索相关接口"])


@search_router.post("/vector", summary="基于向量的搜索接口")
async def vector_search(req: SearchRequest):
    """基于向量的搜索接口

    参数:
    - query (str): 搜索关键词

    返回:
    - dict: 包含搜索结果的字典
    """
    # 这里可以添加实际的业务逻辑，例如使用向量数据库进行搜索
    data = await SearchService.vector_search(
        dataset_ids=req.dataset_ids,
        query=req.query,
        query_filter=req.query_filter,
        top_k=req.top_k,
        score=req.score,
        rerank_model=req.rerank_model,
        rerank_model_provider=req.rerank_model_provider,
    )
    return SuccessResponse(data=data)


@search_router.post("/full-text", description="全文检索")
async def full_text_search(req: SearchRequest):
    """"""
    data = await SearchService.full_text_search(
        dataset_ids=req.dataset_ids,
        query=req.query,
        query_filter=req.query_filter,
        top_k=req.top_k,
        score=req.score,
        rerank_model=req.rerank_model,
        rerank_model_provider=req.rerank_model_provider,
    )
    return SuccessResponse(data=data)


@search_router.post("/hybrid", description="混合检索")
async def hybrid_search(req: SearchRequest):
    """"""
    data = await SearchService.hybrid_search(
        dataset_ids=req.dataset_ids,
        query=req.query,
        query_filter=req.query_filter,
        top_k=req.top_k,
        score=req.score,
        rerank_model=req.rerank_model,
        rerank_model_provider=req.rerank_model_provider,
    )
    return SuccessResponse(data=data)
