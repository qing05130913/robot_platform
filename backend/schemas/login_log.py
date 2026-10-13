"""登录日志相关响应模型。"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LoginLogInfo(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    result: str
    created_at: datetime


class LoginLogListResponse(BaseModel):
    code: int
    message: str
    data: List[LoginLogInfo]
