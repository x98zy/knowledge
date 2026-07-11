from enum import Enum


class ResponseCode(Enum):
    """API 响应状态码枚举"""

    # 自定义成功,可以根据需要添加更多的成功状态码
    SUCCESS = (200, "成功")
    CREATED = (201, "创建成功")
    NO_CONTENT = (204, "操作成功,无返回内容")
    ACCEPTED = (202, "请求已接受,正在处理")

    # HTTP标准错误码
    ERROR = (-1, "请求错误")
    BAD_REQUEST = (400, "参数错误")
    UNAUTHORIZED = (401, "未授权")
    AUTHENTICATION_TIMEOUT = (419, "登录凭证过期")
    FORBIDDEN = (403, "访问受限")
    NOT_FOUND = (404, "资源不存在")
    BAD_METHOD = (405, "不支持的请求方法")
    NOT_ACCEPTABLE = (406, "不接受的请求")
    CONFLICT = (409, "资源冲突")
    GONE = (410, "资源已删除")
    PRECONDITION_FAILED = (412, "前提条件失败")
    UNSUPPORTED_MEDIA_TYPE = (415, "不支持的媒体类型")
    UNPROCESSABLE_ENTITY = (422, "无法处理的实体")
    TOO_MANY_REQUESTS = (429, "请求过于频繁")

    # 服务器错误码
    INTERNAL_SERVER_ERROR = (500, "服务器内部错误")
    NOT_IMPLEMENTED = (501, "功能未实现")
    BAD_GATEWAY = (502, "网关错误")
    SERVICE_UNAVAILABLE = (503, "服务不可用")
    GATEWAY_TIMEOUT = (504, "网关超时")
    HTTP_VERSION_NOT_SUPPORTED = (505, "HTTP版本不支持")

    # 自定义用户错误
    USER_NOT_FOUND = (1001, "用户不存在")
    INVALID_CREDENTIALS = (1002, "无效的凭据")
    ACCOUNT_LOCKED = (1003, "账户已被锁定")
    NOT_AUTHORIZED = (1004, "未授权访问")
    PASSWORD_TOO_WEAK = (1005, "密码过于简单")
    PASSWORD_NOT_MATCH = (1006, "两次输入的密码不匹配")
    USER_ALREADY_EXISTS = (1007, "用户已存在")
    USER_NOT_PERMISSION = (1008, "用户权限不足")

    # 自定义认证错误
    TOKEN_EXPIRED = (1009, "Token 已过期")
    INVALID_TOKEN = (1010, "无效的 Token")
    INVALID_TOKEN_TYPE = (1011, "无效的 Token 类型")

    # 自定义知识库错误
    KNOWLEDGE_BASE_NOT_FOUND = (2001, "知识库不存在")
    EMBEDDING_MODEL_NOT_FOUND = (2002, "嵌入模型不存在")
    FILE_TYPE_NOT_SUPPORTED = (2003, "不支持的文件类型")
    FILE_TOO_LARGE = (2004, "文件过大")
    EMBEDDING_MODEL_INVALID = (2005, "无效的嵌入模型")

    def __init__(self, code: int, message: str):
        self._code = code
        self._message = message

    @property
    def code(self) -> int:
        """返回状态码"""
        return self._code

    @property
    def message(self) -> str:
        """返回状态消息"""
        return self._message
