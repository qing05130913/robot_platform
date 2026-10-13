"""登录日志相关接口。"""
from fastapi import APIRouter, Depends

from schemas.login_log import LoginLogListResponse
from services.login_log_service import list_login_logs
from utils.auth import get_current_user

router = APIRouter(tags=["login-logs"])


@router.get("/login-logs", response_model=LoginLogListResponse)
def get_login_logs(current_user: dict = Depends(get_current_user)):
    """获取登录日志：admin 查看全部，普通用户仅查看自己的日志。"""
    user_id = None if current_user["role"] == "admin" else current_user["user_id"]
    return {"code": 0, "message": "success", "data": list_login_logs(user_id)}
