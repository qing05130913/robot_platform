"""认证相关接口。"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from schemas.auth import LoginRequest, LoginResponse
from services.auth_service import AuthError, login

router = APIRouter(tags=["auth"])

# 业务 code -> HTTP 状态码
_CODE_STATUS = {
    10001: 401,  # 用户不存在
    10002: 401,  # 密码错误
    10003: 403,  # 用户被禁用
}


@router.post("/login", response_model=LoginResponse)
def login_endpoint(payload: LoginRequest):
    try:
        data = login(payload.username, payload.password)
    except AuthError as exc:
        return JSONResponse(
            status_code=_CODE_STATUS.get(exc.code, 400),
            content={"code": exc.code, "message": exc.message, "data": None},
        )
    return {"code": 0, "message": "success", "data": data}
