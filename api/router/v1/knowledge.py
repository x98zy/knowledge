from fastapi import APIRouter

knowledge_router = APIRouter(prefix="/knowledge", tags=["知识相关接口"])


@knowledge_router.get("/{knowledge_id}/detail", summary="获取知识详情")
async def get_knowledge_detail(knowledge_id: str):
    """获取知识详情接口

    参数:
    - knowledge_id (int): 知识 ID

    返回:
    - dict: 包含知识详情的字典
    """
    # 这里可以添加实际的业务逻辑，例如从数据库中查询知识详情
    return {
        "knowledge_id": knowledge_id,
        "title": f"知识标题 {knowledge_id}",
        "content": f"这是知识 {knowledge_id} 的详细内容。",
    }
