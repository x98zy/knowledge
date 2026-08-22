from fastapi import APIRouter, Depends, Query

from common.response import SuccessResponse
from middleware.auth import CurrentUser, get_current_user
from router.v1.entites.file import CreateKnowledgeFileRequest, KnowledgeFileListRequest
from service.file import FileService

file_router = APIRouter(prefix="/file", tags=["文件相关接口"])


@file_router.get("/{knowledge_id}/list", summary="获取知识库文件列表")
async def file_list(
    knowledge_id: str,
    req: KnowledgeFileListRequest = Query(..., description="分页参数"),
    current_user: CurrentUser = Depends(get_current_user),
):
    page_info = await FileService.file_list(
        user_id=current_user.user_id,
        page=req.page,
        page_size=req.page_size,
        keyword=req.keyword,
        knowledge_id=knowledge_id,
    )
    return SuccessResponse(message="获取文件列表成功", data=page_info.model_dump())


@file_router.post("/create", summary="创建文件")
async def create_file(req: CreateKnowledgeFileRequest, current_user: CurrentUser = Depends(get_current_user)):
    """创建文件接口

    参数:
    - req (CreateKnowledgeFileRequest): 创建文件请求体
    - current_user (CurrentUser): 当前用户信息

    返回:
    - dict: 包含创建结果的字典
    """
    # 这里可以添加实际的业务逻辑，例如将文件信息保存到数据库
    success = await FileService.create_file(
        user_id=current_user.user_id,
        dataset_id=req.dataset_id,
        enable_semantic=req.enable_semantic,
        file_key=req.file_key,
        segment_mode=req.segment_mode,
        pre_rule=req.pre_rule,
        max_tokens=req.max_tokens,
        overlap=req.overlap,
        delimiter=req.delimiter,
        parent_mode=req.parent_mode,
        child_delimiter=req.child_delimiter,
        child_overlap=req.child_overlap,
        child_max_tokens=req.child_max_tokens,
    )
    return SuccessResponse(message="文件创建成功", data={"success": success})


@file_router.delete("/{file_id}", summary="删除文件")
async def delete_file(file_id: str, current_user: CurrentUser = Depends(get_current_user)):
    success = await FileService.delete_file(file_id=file_id, user_id=current_user.user_id)
    return SuccessResponse(message="文件删除成功", data={"success": success})


@file_router.delete("/{file_id}/delete", summary="删除文件（已废弃，请使用 DELETE /file/{file_id}）", include_in_schema=False)
async def delete_file_deprecated(file_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """向后兼容：旧路径 /file/{file_id}/delete 映射到新实现，避免前端尚未切换时报错。"""
    return await delete_file(file_id=file_id, current_user=current_user)
