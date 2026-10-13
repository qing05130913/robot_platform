"""管理员后台相关响应模型。"""
from pydantic import BaseModel


class StatisticsInfo(BaseModel):
    user_count: int
    device_count: int
    online_count: int
    offline_count: int
    average_battery: float


class StatisticsResponse(BaseModel):
    code: int
    message: str
    data: StatisticsInfo
