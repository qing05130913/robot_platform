"""用户相关接口。"""
from fastapi import APIRouter, Depends, HTTPException

from schemas.user import UserListResponse, UserResponse
from services.user_service import get_user_by_id, list_users
from utils.auth import get_current_user

router = APIRouter(tags=["users"])


@router.get("/user", response_model=UserResponse)
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return {"code": 0, "message": "success", "data": current_user}


@router.get("/users", response_model=UserListResponse)
def get_users(current_user: dict = Depends(get_current_user)):
    """获取用户列表（仅 admin）。"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail={"code": 10403, "message": "无权限访问"})
    return {"code": 0, "message": "success", "data": list_users()}


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """查询指定用户信息（admin 可查任意，普通用户仅可查自己）。"""
    if current_user["role"] != "admin" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail={"code": 10403, "message": "无权限访问"})

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": 10404, "message": "用户不存在"})

    return {"code": 0, "message": "success", "data": user}
