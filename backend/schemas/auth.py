"""认证相关的请求 / 响应模型。"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=255, description="密码")

    @field_validator("username", "password")
    @classmethod
    def _strip_and_check(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class LoginData(BaseModel):
    token: str
    user_id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    code: int
    message: str
    data: Optional[LoginData] = None
