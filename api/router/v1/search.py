from fastapi import APIRouter

search_router = APIRouter(prefix="/search", tags=["搜索相关接口"])


@search_router.post("/vector", summary="基于向量的搜索接口")
async def vector_search(query: str):
    """基于向量的搜索接口

    参数:
    - query (str): 搜索关键词

    返回:
    - dict: 包含搜索结果的字典
    """
    # 这里可以添加实际的业务逻辑，例如使用向量数据库进行搜索
    return {
        "query": query,
        "results": [
            {"knowledge_id": "1", "title": "知识标题 1", "content": "这是知识 1 的详细内容。"},
            {"knowledge_id": "2", "title": "知识标题 2", "content": "这是知识 2 的详细内容。"},
        ],
    }
