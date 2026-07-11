from fastapi import APIRouter, Depends, Request, UploadFile

from common.code import ResponseCode
from common.jwt import create_access_token, create_refresh_token, decode_token
from common.response import ErrorResponse, SuccessResponse
from middleware.auth import CurrentUser, get_current_user
from middleware.rate_limit import RateLimiter
from schemas.auth import LoginRequest, RefreshRequest, RefreshTokenResponse, TokenResponse, ChangePasswordRequest
from schemas.user import RegisterRequest
from service.user_service import UserService

user_router = APIRouter(prefix="/user", tags=["用户相关接口"])

rate_limiter = RateLimiter(prefix="rate_limit:register")


@user_router.get("/profile", summary="获取用户信息")
async def get_user_profile(current_user: CurrentUser = Depends(get_current_user)):
    """获取用户信息接口(需认证)

    参数:
    - current_user (CurrentUser): 当前用户

    返回:
    - SuccessResponse: 包含用户信息的字典
    """
    user_info = await UserService.get_user_profile(current_user.user_id)
    return SuccessResponse(data=user_info)


@user_router.post("/register", summary="用户注册")
async def register(request: Request, req: RegisterRequest):
    """用户注册接口

    参数:
    - req (RegisterRequest): 注册请求体，包含 username, email, password

    返回:
    - SuccessResponse: 注册成功的用户信息
    """
    client_ip = request.client.host
    if not await rate_limiter.check_rate_limit(client_ip, max_requests=5, window=60):
        return ErrorResponse(
            message=ResponseCode.TOO_MANY_REQUESTS.message,
            code=ResponseCode.TOO_MANY_REQUESTS.code,
            status_code=429,
        )

    user = await UserService.register(
        username=req.username,
        email=req.email,
        password=req.password,
    )
    return SuccessResponse(
        message="注册成功",
        code=ResponseCode.CREATED.code,
        data=user.dict,
        status_code=201,
    )


@user_router.post("/login", summary="用户登录")
async def login(req: LoginRequest):
    """用户登录接口

    参数:
    - req (LoginRequest): 登录请求体, 包含 username, password

    返回:
    - TokenResponse: 包含 access_token, refresh_token, token_type
    """
    user = await UserService.login(username=req.username, password=req.password)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@user_router.post("/token/refresh", summary="刷新 Token")
async def refresh_token(req: RefreshRequest):
    """刷新 access token

    参数:
    - req (RefreshRequest): 刷新请求体, 包含 refresh_token

    返回:
    - RefreshTokenResponse: 包含新的 access_token
    """
    try:
        payload = decode_token(req.refresh_token)
    except Exception:
        return ErrorResponse(
            message="无效的 Refresh Token",
            code=ResponseCode.INVALID_TOKEN.code,
            status_code=401,
        )

    if payload.get("type") != "refresh":
        return ErrorResponse(
            message="无效的 Token 类型",
            code=ResponseCode.INVALID_TOKEN_TYPE.code,
            status_code=401,
        )

    user_id = payload.get("sub")
    new_access_token = create_access_token(user_id)
    return RefreshTokenResponse(access_token=new_access_token)


@user_router.post("/upload_avator", summary="上传用户头像")
async def upload_avator(
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
):
    """上传用户头像接口

    参数:
    - file (UploadFile): 头像文件
    - current_user (CurrentUser): 当前用户

    返回:
    - SuccessResponse: 上传成功的响应
    """
    success = await UserService.upload_avator(file, current_user.user_id)
    return SuccessResponse(message="头像上传成功", data=success)


@user_router.post("/change_password", summary="修改用户密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """修改用户密码接口

    参数:
    - req (ChangePasswordRequest): 修改密码请求体, 包含 old_password, new_password
    - current_user (CurrentUser): 当前用户

    返回:
    - SuccessResponse: 修改成功的响应
    """
    old_password = req.old_password
    new_password = req.new_password

    if not old_password or not new_password:
        return ErrorResponse(
            message="旧密码和新密码不能为空",
            code=ResponseCode.INVALID_INPUT.code,
            status_code=400,
        )

    await UserService.change_password(
        user_id=current_user.user_id,
        old_password=old_password,
        new_password=new_password,
    )
    return SuccessResponse(message="密码修改成功")
