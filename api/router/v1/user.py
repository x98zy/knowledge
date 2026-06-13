from api.common.response import SuccessResponse
from api.service.user_service import UserService
from fastapi import APIRouter

user_router = APIRouter(prefix="/user", tags=["用户相关接口"])


@user_router.get("/{user_id}/profile", summary="获取用户信息")
async def get_user_profile(user_id: int):
    """获取用户信息接口

    参数:
    - user_id (int): 用户 ID

    返回:
    - dict: 包含用户信息的字典
    """
    # 这里可以添加实际的业务逻辑，例如从数据库中查询用户信息
    return {
        "user_id": user_id,
        "username": f"user{user_id}",
        "email": f"user{user_id}@example.com",
    }


@user_router.get("/list", summary="获取用户列表")
async def get_user_list():
    """获取用户列表接口

    返回:
    - list[User]: 包含用户列表的列表
    """
    user_list = await UserService().get_user_list()
    data = [user.dict for user in user_list]
    return SuccessResponse(data=data)
