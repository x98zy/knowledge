from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException

from common.error import CustomException
from common.response import ErrorResponse
from extensions.ext_redis import redis_client


def handler_exception(app: FastAPI) -> None:
    """自定义全局异常处理器"""

    @app.exception_handler(CustomException)
    async def global_exception_handler(request: Request, exc: CustomException) -> ErrorResponse:
        return ErrorResponse(
            message=exc.message,
            code=exc.code,
            data=exc.data,
            success=exc.success,
            status_code=exc.status_code,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> ErrorResponse:
        return ErrorResponse(
            message=exc.detail,
            code=exc.status_code,
            data=None,
            success=False,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> ErrorResponse:
        """
        请求参数验证异常处理器

        参数:
        - request (Request): 请求对象。
        - exc (RequestValidationError): 请求参数验证异常实例。

        返回:
        - ErrorResponse: 包含错误信息的错误响应。
        """
        error_mapping = {
            "Field required": "请求失败，缺少必填项！",
            "value is not a valid list": "类型错误，提交参数应该为列表！",
            "value is not a valid int": "类型错误，提交参数应该为整数！",
            "value could not be parsed to a boolean": "类型错误，提交参数应该为布尔值！",
            "Input should be a valid list": "类型错误，输入应该是一个有效的列表！",
        }
        raw_msg = exc.errors()[0].get("msg")
        msg = error_mapping.get(raw_msg, raw_msg)
        # 去掉Pydantic默认的前缀“Value error”, 仅保留具体提示内容
        if isinstance(msg, str) and msg.startswith("Value error"):
            msg = msg.split(",", 1)[1].strip() if "," in msg else msg.replace("Value error", "").strip()
        return ErrorResponse(
            message=str(msg),
            status_code=422,
            data=exc.body,
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(request: Request, exc: ResponseValidationError) -> ErrorResponse:
        """
        响应参数验证异常处理器

        参数:
        - request (Request): 请求对象。
        - exc (ResponseValidationError): 响应参数验证异常实例。

        返回:
        - ErrorResponse: 包含错误信息的错误响应。
        """
        return ErrorResponse(
            message="服务器响应格式错误",
            status_code=500,
            data=exc.body,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> ErrorResponse:
        return ErrorResponse(
            message="服务器发生未知错误",
            data=str(exc),
            status_code=500,
        )


def register_exception_handler(app: FastAPI) -> None:
    """注册全局异常处理器"""
    handler_exception(app)


def register_router(app: FastAPI) -> None:
    """注册路由"""
    from router import knowledge_router, search_router, user_router

    app.include_router(knowledge_router)
    app.include_router(search_router)
    app.include_router(user_router)


def register_middleware(app: FastAPI) -> None:
    """注册中间件"""
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from middleware.auth import AuthMidllerWare
    from middleware.db_context import DBContextMiddleware

    app.add_middleware(AuthMidllerWare)
    app.add_middleware(DBContextMiddleware)


def init_app(app: FastAPI) -> FastAPI:
    register_exception_handler(app)
    register_router(app)
    register_middleware(app)

    @app.on_event("shutdown")
    async def shutdown():
        await redis_client.close()

    return app
