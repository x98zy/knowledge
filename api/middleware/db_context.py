from api.config.settings import settings
from api.extensions.ext_db import async_session_factory, context_db_session, db
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

NO_DB_CONTEXT_PATHS = ["/docs", "/openapi.json"]


class DbContext:
    """数据库上下文类"""

    def __init__(self, request: Request):
        self.request = request
        self.token = None

    async def __aenter__(self):
        # 在上下文管理器进入时创建数据库连接
        config = settings.FASTAPI_CONFIG
        real_path = self.request.url.path.replace(config.get("root_path", ""), "")
        if real_path in NO_DB_CONTEXT_PATHS:
            return self
        session = context_db_session.get(None)
        if session:
            return self
        self.token = db.set_session(async_session_factory())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 在上下文管理器退出时关闭数据库连接
        session = context_db_session.get(None)
        try:
            session = context_db_session.get(None)
            if session is not None:
                if exc_type is None:
                    await session.commit()
                else:
                    await session.rollback()
        finally:
            if session is not None:
                await session.close()
            if self.token is not None:
                db.reset_session(self.token)


class DBContextMiddleware(BaseHTTPMiddleware):
    """数据库上下文中间件"""

    async def dispatch(self, request, call_next):
        async with DbContext(request):
            responser = await call_next(request)
            return responser
