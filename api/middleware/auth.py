from dataclasses import dataclass

from fastapi import Header, Request
from jose.exceptions import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from common.code import ResponseCode
from common.error import CustomException
from common.jwt import decode_token
from config.settings import settings

NO_LOGIN_PATHS = ["/user/login", "/token/refresh", "/user/register"]


@dataclass
class CurrentUser:
    """Authenticated user context, injected via Depends."""

    user_id: str


def get_current_user(authorization: str | None = Header(None)) -> CurrentUser:
    """Extract and validate JWT token from the Authorization header.

    Expects: Authorization: Bearer <token>
    Returns: CurrentUser with user_id
    Raises: CustomException(401) on missing, invalid, or expired token
    """
    if not authorization:
        raise CustomException(
            message="未提供认证凭据",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    if not str(authorization).strip():
        raise CustomException(
            message="未提供认证凭据",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise CustomException(
            message="无效的认证格式",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    token = parts[1]

    try:
        payload = decode_token(token)
    except JWTError:
        raise CustomException(  # noqa: B904
            message="无效的 Token 格式",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    if payload.get("type") != "access":
        raise CustomException(
            message="无效的 Token 类型",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    user_id = payload.get("sub")
    if not user_id:
        raise CustomException(
            message="无效的 Token",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    return CurrentUser(user_id=user_id)


class AuthMidllerWare(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        config = settings.FASTAPI_CONFIG
        real_path = request.url.path.replace(config.get("root_path", ""), "")
        if real_path not in NO_LOGIN_PATHS:
            try:
                current_user = get_current_user(request.headers.get("Authorization"))
                if not current_user:
                    raise CustomException(
                        message="未提供认证凭据",
                        code=ResponseCode.UNAUTHORIZED.code,
                        status_code=401,
                    )
                request.state.current_user = current_user
            except CustomException:
                return JSONResponse(
                    content={
                        "message": "无效的登录凭证",
                        "code": ResponseCode.UNAUTHORIZED.code,
                        "data": None,
                        "success": False,
                    },
                    status_code=401,
                )
        return await call_next(request)
