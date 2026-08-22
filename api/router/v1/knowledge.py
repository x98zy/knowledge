from fastapi import APIRouter, Body, Depends, Query, UploadFile

from common.code import ResponseCode
from common.response import ErrorResponse, SuccessResponse
from middleware.auth import CurrentUser, get_current_user
from router.v1.entites.dataset import CreateDatasetRequest, KnowledgeListRequest
from schemas.knowledge import EmbeddingListResponse, EmbeddingModel
from service.knowledge import KnowledgeService

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


@knowledge_router.get("/get_embedding_models", summary="获取嵌入模型列表")
async def get_embedding_models():
    """获取嵌入模型列表接口

    返回:
    - dict: 包含嵌入模型列表的字典
    """
    embedding_modles = await KnowledgeService.get_embedding_models()
    return SuccessResponse(
        message="获取嵌入模型列表成功",
        data=EmbeddingListResponse(
            models=[EmbeddingModel(model=model.name, provider=model.provider) for model in embedding_modles]
        ),
    )


@knowledge_router.post("/create", summary="创建知识库")
async def create_knowledge(
    req: CreateDatasetRequest = Body(...), current_user: CurrentUser = Depends(get_current_user)
):
    """创建知识库接口

    返回:
    - dict: 包含创建结果的字典
    """
    record = await KnowledgeService.create_knowledge(
        name=req.name,
        description=req.description,
        embedding_model=req.embedding_model,
        embedding_provider=req.embedding_provider,
        user_id=current_user.user_id,
    )
    return SuccessResponse(message="知识库创建成功", data={"id": record.id, "name": record.name}, status_code=201)


@knowledge_router.post("/upload_file", summary="上传文件到阿里云 OSS")
async def upload_file(
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    """接收前端上传的文件, 上传至阿里云 OSS 并登记到数据库.

    Body (multipart/form-data):
    - file: 文件内容

    流程:
    1. 将上传文件暂存到临时目录
    2. 计算文件 SHA256 哈希
    3. 生成 OSS 文件 Key (格式: uploads/{uuid}.{ext})
    4. 调用 AliYunOSS 上传到 OSS
    5. 写入 upload_files 表
    6. 返回文件信息
    """
    record = await KnowledgeService.upload_file(file, current_user.user_id)

    return SuccessResponse(
        message="文件上传成功",
        code=ResponseCode.CREATED.code,
        data={
            "id": record.id,
            "file_name": record.file_name,
            "file_key": record.file_key,
            "file_size": record.file_size,
            "ext": record.ext,
        },
        status_code=201,
    )


@knowledge_router.get("/list", summary="获取知识库列表")
async def get_knowledge_list(
    req: KnowledgeListRequest = Query(..., description="分页参数"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取知识库列表接口"""
    page_info = await KnowledgeService.get_knowledge_list(
        user_id=current_user.user_id, page=req.page, page_size=req.page_size, keyword=req.keyword
    )
    return SuccessResponse(message="获取知识库列表成功", data=page_info.model_dump())


@knowledge_router.delete("/{knowledge_id}/detail")
async def delete_knowledge(knowledge_id: str, current_user: CurrentUser = Depends(get_current_user)):
    success, msg = await KnowledgeService.delete_knowledge(knowledge_id, current_user.user_id)
    if success:
        return SuccessResponse(message="知识库正在进行后台异步删除")
    else:
        return ErrorResponse(message=msg, code=ResponseCode.ERROR.code)
