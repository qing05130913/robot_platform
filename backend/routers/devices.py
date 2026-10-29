"""设备相关接口。"""
from fastapi import APIRouter, Depends, HTTPException

from schemas.device import (
    DeviceBatteryUpdate,
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceStatusUpdate,
    DeviceUpdateResponse,
    OperationLogListResponse,
)
from services.device_service import (
    create_device as create_device_service,
    delete_device as delete_device_service,
    get_device,
    get_device_by_name,
    list_devices,
    list_operation_logs,
    update_device_battery,
    update_device_status,
)
from utils.auth import get_current_user

router = APIRouter(tags=["devices"])


def _get_accessible_device(device_id: int, current_user: dict) -> dict:
    """校验设备存在性与访问权限，返回设备信息。

    普通用户对不存在的设备也返回 403（而非 404），避免泄露设备是否存在，
    与用户接口的越权口径保持一致。
    """
    device = get_device(device_id)
    if device is None:
        # admin 有权知道"不存在"；普通用户一律 403，不暴露设备是否存在
        if current_user["role"] == "admin":
            raise HTTPException(status_code=404, detail={"code": 10404, "message": "设备不存在"})
        raise HTTPException(status_code=403, detail={"code": 10403, "message": "无权限访问"})
    if current_user["role"] != "admin" and device["owner_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail={"code": 10403, "message": "无权限访问"})
    return device


@router.get("/devices", response_model=DeviceListResponse)
def get_devices(current_user: dict = Depends(get_current_user)):
    """获取设备列表：admin 返回全部，普通用户仅返回自己的设备。"""
    owner_id = None if current_user["role"] == "admin" else current_user["user_id"]
    return {"code": 0, "message": "success", "data": list_devices(owner_id)}


@router.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device_detail(device_id: int, current_user: dict = Depends(get_current_user)):
    """获取设备详情：admin 可查任意设备，普通用户仅可查自己的设备。"""
    device = _get_accessible_device(device_id, current_user)
    return {"code": 0, "message": "success", "data": device}


@router.post("/devices", response_model=DeviceResponse)
def create_device(payload: DeviceCreate, current_user: dict = Depends(get_current_user)):
    """创建设备：owner_id 由当前登录用户自动确定，不接受客户端传入。"""
    if get_device_by_name(payload.name) is not None:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "设备名称已存在"})
    device = create_device_service(
        payload.name,
        current_user["user_id"],
        payload.status,
        payload.battery,
    )
    return {"code": 0, "message": "success", "data": device}


@router.delete("/devices/{device_id}", response_model=DeviceUpdateResponse)
def delete_device(device_id: int, current_user: dict = Depends(get_current_user)):
    """删除设备：admin 可删任意设备，普通用户仅可删自己的设备。"""
    _get_accessible_device(device_id, current_user)
    delete_device_service(device_id)
    return {"code": 0, "message": "success", "data": None}


@router.put("/devices/{device_id}/status", response_model=DeviceUpdateResponse)
def update_status(
    device_id: int,
    payload: DeviceStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    """修改设备状态（并写入操作日志）。"""
    _get_accessible_device(device_id, current_user)
    update_device_status(device_id, payload.status, current_user["user_id"])
    return {"code": 0, "message": "success", "data": None}


@router.put("/devices/{device_id}/battery", response_model=DeviceUpdateResponse)
def update_battery(
    device_id: int,
    payload: DeviceBatteryUpdate,
    current_user: dict = Depends(get_current_user),
):
    """修改设备电量（并写入操作日志）。"""
    _get_accessible_device(device_id, current_user)
    update_device_battery(device_id, payload.battery, current_user["user_id"])
    return {"code": 0, "message": "success", "data": None}


@router.get("/operation-logs", response_model=OperationLogListResponse)
def get_operation_logs(current_user: dict = Depends(get_current_user)):
    """获取操作日志：admin 查看全部，普通用户仅查看自己的日志。"""
    user_id = None if current_user["role"] == "admin" else current_user["user_id"]
    return {"code": 0, "message": "success", "data": list_operation_logs(user_id)}
