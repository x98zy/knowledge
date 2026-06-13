from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .code import ResponseCode


class ResponseSchema(BaseModel):
    """统一响应模型"""

    success: bool = Field(..., description="是否成功")
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="状态描述")
    data: Any | None = Field(None, description="响应数据")


class SuccessResponse(JSONResponse):
    """成功响应类"""

    def __init__(
        self,
        message: str = ResponseCode.SUCCESS.message,
        code: int = ResponseCode.SUCCESS.code,
        data: Any | None = None,
        success: bool = True,
        status_code: int = 200,
    ):
        content = ResponseSchema(success=success, code=code, message=message, data=data).model_dump()
        super().__init__(content=content, status_code=status_code)


class ErrorResponse(JSONResponse):
    """错误响应类"""

    def __init__(
        self,
        message: str = ResponseCode.ERROR.message,
        code: int = ResponseCode.ERROR.code,
        data: Any | None = None,
        success: bool = False,
        status_code: int = 500,
    ):
        content = ResponseSchema(success=success, code=code, message=message, data=data).model_dump()
        super().__init__(content=content, status_code=status_code)
