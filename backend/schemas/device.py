"""设备相关请求 / 响应模型。"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    id: int
    name: str
    owner_id: int
    status: str
    battery: int


class DeviceStatusUpdate(BaseModel):
    status: Literal["online", "offline", "error"]


class DeviceBatteryUpdate(BaseModel):
    battery: int = Field(..., ge=0, le=100, description="电量 0-100")


class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    status: Literal["online", "offline", "error"] = "offline"
    battery: int = Field(0, ge=0, le=100)


class DeviceResponse(BaseModel):
    code: int
    message: str
    data: DeviceInfo


class DeviceListResponse(BaseModel):
    code: int
    message: str
    data: List[DeviceInfo]


class DeviceUpdateResponse(BaseModel):
    code: int
    message: str
    data: Optional[DeviceInfo] = None


class OperationLogInfo(BaseModel):
    id: int
    user_id: int
    device_id: int
    action: str
    created_at: datetime


class OperationLogListResponse(BaseModel):
    code: int
    message: str
    data: List[OperationLogInfo]
