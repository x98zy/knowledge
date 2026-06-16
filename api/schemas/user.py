import re

from api.common.weak_passwords import WEAK_PASSWORDS
from pydantic import BaseModel, field_validator, model_validator


class RegisterRequest(BaseModel):
    """用户注册请求体"""

    username: str
    email: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("用户名长度至少 3 个字符")
        if len(v) > 50:
            raise ValueError("用户名长度不能超过 50 个字符")
        if not re.match(r"^[a-zA-Z0-9_一-龥]+$", v):
            raise ValueError("用户名只能包含字母、数字、下划线和中文")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度至少 8 位")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母、小写字母、数字和特殊字符")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含大写字母、小写字母、数字和特殊字符")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含大写字母、小写字母、数字和特殊字符")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?~`]", v):
            raise ValueError("密码必须包含大写字母、小写字母、数字和特殊字符")
        if v.lower() in WEAK_PASSWORDS:
            raise ValueError("密码过于简单, 请使用更复杂的密码")
        return v

    @model_validator(mode="after")
    def validate_password_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self
