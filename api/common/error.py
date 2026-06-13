from typing import Any

from fastapi import status

from .code import ResponseCode


class CustomException(Exception):
    """自定义异常类"""

    def __init__(
        self,
        message: ResponseCode.ERROR.message,
        code: int = ResponseCode.ERROR.code,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: Any | None = None,
        success: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data
        self.success = success

    def __str__(self) -> str:
        return self.message
