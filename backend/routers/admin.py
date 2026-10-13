"""管理员专用接口。"""
from fastapi import APIRouter, Depends, HTTPException

from schemas.admin import StatisticsResponse
from schemas.device import DeviceListResponse
from services.admin_service import get_statistics
from services.device_service import list_devices
from utils.auth import get_current_user

router = APIRouter(tags=["admin"])


@router.get("/admin/devices", response_model=DeviceListResponse)
def admin_list_devices(current_user: dict = Depends(get_current_user)):
    """管理员查看全部设备（普通用户 403）。"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail={"code": 10403, "message": "无权限访问"})
    return {"code": 0, "message": "success", "data": list_devices(None)}


@router.get("/admin/statistics", response_model=StatisticsResponse)
def admin_statistics(current_user: dict = Depends(get_current_user)):
    """管理员查看后台统计数据（普通用户 403）。"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail={"code": 10403, "message": "无权限访问"})
    return {"code": 0, "message": "success", "data": get_statistics()}
