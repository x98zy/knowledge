from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose.exceptions import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from common.code import ResponseCode
from common.error import CustomException
from common.jwt import decode_token
from config.settings import settings

NO_LOGIN_PATHS = ["/user/login", "/user/token/refresh", "/user/register", "/docs", "/docs/oauth2-redirect", "/openapi.json"]

_bearer_scheme = HTTPBearer()


@dataclass
class CurrentUser:
    """Authenticated user context, injected via Depends."""

    user_id: str


def _validate_token(token: str) -> CurrentUser:
    """校验 JWT token 字符串, 返回 CurrentUser."""
    if not token or not token.strip():
        raise CustomException(
            message="未提供认证凭据",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    parts = token.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise CustomException(
            message="无效的认证格式",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        )

    try:
        payload = decode_token(parts[1])
    except JWTError as err:
        raise CustomException(
            message="无效的 Token 格式",
            code=ResponseCode.UNAUTHORIZED.code,
            status_code=401,
        ) from err

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
    delta = payload.get("exp")
    # 判断登录凭证是否过期
    if int((datetime.now(timezone.utc)).timestamp()) > int(delta):
        raise CustomException(
            message="登录凭证已过期",
            code=ResponseCode.AUTHENTICATION_TIMEOUT.code,
            status_code=401,
        )

    return CurrentUser(user_id=user_id)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> CurrentUser:
    """接口层依赖注入 — 从 Swagger Authorize 自动注入 Authorization header."""
    return _validate_token(f"Bearer {credentials.credentials}")


class AuthMidllerWare(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == 'OPTIONS':
            return await call_next(request)
        config = settings.FASTAPI_CONFIG
        real_path = request.url.path.replace(config.get("root_path", ""), "")
        if real_path not in NO_LOGIN_PATHS:
            try:
                auth_header = request.headers.get("Authorization", "")
                current_user = _validate_token(auth_header)
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
