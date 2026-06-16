from api.common.code import ResponseCode
from api.common.jwt import create_access_token, create_refresh_token, decode_token
from api.common.response import ErrorResponse, SuccessResponse
from api.middleware.rate_limit import RateLimiter
from api.schemas.auth import LoginRequest, RefreshRequest, RefreshTokenResponse, TokenResponse
from api.schemas.user import RegisterRequest
from api.service.user_service import UserService
from fastapi import APIRouter, Request

user_router = APIRouter(prefix="/user", tags=["用户相关接口"])

rate_limiter = RateLimiter(prefix="rate_limit:register")


@user_router.get("/{user_id}/profile", summary="获取用户信息")
async def get_user_profile(user_id: int):
    """获取用户信息接口(需认证)

    参数:
    - user_id (int): 用户 ID

    返回:
    - dict: 包含用户信息的字典
    """
    return {
        "user_id": user_id,
        "message": "认证成功",
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

    user = await UserService().register(
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
    user = await UserService().login(username=req.username, password=req.password)
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
