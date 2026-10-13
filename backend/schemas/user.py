"""用户相关响应模型。"""
from typing import List

from pydantic import BaseModel


class UserInfo(BaseModel):
    user_id: int
    username: str
    role: str
    status: str


class UserResponse(BaseModel):
    code: int
    message: str
    data: UserInfo


class UserListResponse(BaseModel):
    code: int
    message: str
    data: List[UserInfo]
