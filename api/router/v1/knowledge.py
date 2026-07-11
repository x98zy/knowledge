from fastapi import APIRouter, Body, Depends, UploadFile

from common.code import ResponseCode
from common.response import SuccessResponse
from middleware.auth import CurrentUser, get_current_user
from router.v1.entites.dataset import CreateDatasetRequest
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
    return EmbeddingListResponse(
        models=[EmbeddingModel(model=model.name, provider=model.provider) for model in embedding_modles]
    )


@knowledge_router.post("/create", summary="创建知识库")
async def create_knowledge(req: CreateDatasetRequest = Body(...)):
    """创建知识库接口

    返回:
    - dict: 包含创建结果的字典
    """
    return {"message": "知识库创建成功"}


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
