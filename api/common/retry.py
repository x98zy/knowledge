"""异常分类器：区分「瞬时错误（可重试）」与「永久错误（不应重试）」。

设计原则
--------
1. 白名单制 + 默认安全：只有明确的网络抖动/超时/限流/服务端 5xx 才算瞬时错误，
   未识别的异常一律视为永久错误，避免「毒消息」被 NACK 无限重投（并重复计费）。
2. 业务异常（CustomException）、参数/格式错误（ValueError、JSONDecodeError、
   NotImplementedError 等）不重试。
3. 沿异常因果链（raise X from e、except 中再抛）向上查找，防止真实根因被
   RuntimeError 等包装后误判为永久错误。

典型用法（FastStream worker）::

    except Exception as e:
        if is_retryable(e):
            raise                       # 交给 NACK_ON_ERROR 重投
        # 永久错误：落业务终态后 return，消息正常 ACK
"""

import asyncio
import builtins

import httpx
from sqlalchemy.exc import OperationalError as SAOperationalError
from sqlalchemy.exc import TimeoutError as SATimeoutError

from common.error import CustomException


class RetryableError(Exception):
    """瞬时错误标记：调用方可主动抛出本类明确声明「该错误可安全重试」。"""


# 可重试的 HTTP 状态码：客户端超时 / 提前数据 / 限流 / 服务端临时故障
RETRYABLE_HTTP_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}

# openai SDK（DashScope 兼容接口同样使用它）：超时、连接失败、429、5xx
try:
    from openai import APIConnectionError as _OpenAIAPIConnectionError
    from openai import APIStatusError as _OpenAIAPIStatusError
    from openai import APITimeoutError as _OpenAIAPITimeoutError
    from openai import InternalServerError as _OpenAIInternalServerError
    from openai import RateLimitError as _OpenAIRateLimitError

    _OPENAI_RETRYABLE: tuple[type[BaseException], ...] = (
        _OpenAIAPITimeoutError,
        _OpenAIAPIConnectionError,
        _OpenAIRateLimitError,
        _OpenAIInternalServerError,
    )
except ImportError:  # pragma: no cover - 环境缺依赖时降级
    _OpenAIAPIStatusError = None
    _OPENAI_RETRYABLE = ()

# redis-py：连接断开/命令超时
try:
    from redis.exceptions import ConnectionError as _RedisConnectionError
    from redis.exceptions import TimeoutError as _RedisTimeoutError

    _REDIS_RETRYABLE: tuple[type[BaseException], ...] = (_RedisConnectionError, _RedisTimeoutError)
except ImportError:  # pragma: no cover
    _REDIS_RETRYABLE = ()

# asyncmy 直连错误（一般已被 SQLAlchemy 包装成 OperationalError，这里兜底）
try:
    from asyncmy.errors import OperationalError as _AsyncmyOperationalError
except ImportError:  # pragma: no cover
    _AsyncmyOperationalError = None

# Milvus：仅「限流」明确可重试；集合不存在(100)等是永久错误
try:
    from pymilvus.exceptions import ErrorCode as _MilvusErrorCode
    from pymilvus.exceptions import MilvusException as _MilvusException
except ImportError:  # pragma: no cover
    _MilvusException = None
    _MilvusErrorCode = None

# gRPC（pymilvus 连接层偶发直接抛 AioRpcError）
try:
    from grpc import StatusCode as _GrpcStatusCode
    from grpc.aio import AioRpcError as _AioRpcError

    _RETRYABLE_GRPC_CODES = {
        _GrpcStatusCode.UNAVAILABLE,
        _GrpcStatusCode.DEADLINE_EXCEEDED,
        _GrpcStatusCode.RESOURCE_EXHAUSTED,
    }
except ImportError:  # pragma: no cover
    _AioRpcError = None
    _RETRYABLE_GRPC_CODES = set()

# 内置/网络层/数据库连接池白名单
# 注意：asyncio.TimeoutError 在 Python 3.11+ 就是 builtins.TimeoutError 的别名，重复放无副作用
_BASE_RETRYABLE_TYPES: tuple[type[BaseException], ...] = (
    builtins.TimeoutError,
    asyncio.TimeoutError,
    ConnectionError,
    RetryableError,
    # httpx：TimeoutException 及其全部子类；TransportError 覆盖连接重置/断开等网络层错误
    httpx.TimeoutException,
    httpx.TransportError,
    # SQLAlchemy：连接丢失(server has gone away)、死锁、连接池获取超时等
    SAOperationalError,
    SATimeoutError,
)


def _is_single_retryable(exc: BaseException) -> bool:
    """判定单个异常（不沿因果链）是否可重试。"""
    # 业务异常永远是永久失败（如"知识库不存在""没有权限"）
    if isinstance(exc, CustomException):
        return False
    if isinstance(exc, _BASE_RETRYABLE_TYPES):
        return True
    if _OPENAI_RETRYABLE and isinstance(exc, _OPENAI_RETRYABLE):
        return True
    if _REDIS_RETRYABLE and isinstance(exc, _REDIS_RETRYABLE):
        return True
    if _AsyncmyOperationalError is not None and isinstance(exc, _AsyncmyOperationalError):
        return True

    # httpx 显式状态码（HTTPStatusError 不属于 TransportError，需单独按状态码判定）
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_STATUS_CODES

    # openai 其他按状态码区分的错误（覆盖未来新增的 429/5xx 子类）
    if _OpenAIAPIStatusError is not None and isinstance(exc, _OpenAIAPIStatusError):
        status_code = getattr(exc, "status_code", None)
        return status_code in RETRYABLE_HTTP_STATUS_CODES

    # Milvus：仅限流可重试
    if _MilvusException is not None and isinstance(exc, _MilvusException):
        return _MilvusErrorCode is not None and exc.code == _MilvusErrorCode.RATE_LIMIT

    # gRPC：服务不可用 / 截止时间超时 / 资源耗尽
    if _AioRpcError is not None and isinstance(exc, _AioRpcError):
        return exc.code() in _RETRYABLE_GRPC_CODES

    return False


def is_retryable(exc: BaseException | None, max_depth: int = 5) -> bool:
    """判定异常是否属于「可安全重试」的瞬时错误。

    会沿 ``__cause__``（raise from）/ ``__context__``（except 中再抛）因果链向上查找，
    防止根因（如 httpx 超时）被外层 `RuntimeError("xxx失败")` 包装后误判为永久错误。

    Args:
        exc: 捕获到的异常；传 None 时返回 False。
        max_depth: 因果链最大向上查找层数，防止异常循环引用导致死循环。
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    for _ in range(max_depth):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        if _is_single_retryable(current):
            return True
        current = current.__cause__ or current.__context__
    return False
