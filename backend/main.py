"""FastAPI 应用入口。

本文件负责创建 FastAPI 应用、注册业务路由，并统一异常响应格式。
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from database import assert_test_database, get_connection
from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.devices import router as devices_router
from routers.login_logs import router as login_logs_router
from routers.users import router as users_router

# 测试模式安全校验：TEST_MODE=1 时，启动前确认实际连接的是测试库。
assert_test_database()

app = FastAPI(
    title="Robot Platform API",
    description="机器人管理平台后端服务",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(devices_router)
app.include_router(login_logs_router)
app.include_router(admin_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """将 HTTPException 统一转换为业务响应格式 {code, message, data}。"""
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", exc.status_code)
        message = detail.get("message", str(detail))
    else:
        code = exc.status_code
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": message, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """将 422 参数校验失败也统一转换为业务响应格式 {code, message, data}。"""
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数校验失败", "data": jsonable_encoder(exc.errors())},
    )


@app.get("/")
def read_root():
    """健康检查接口：确认服务正常运行。"""
    return {
        "message": "Robot Platform API is running",
        "docs": "/docs",
    }


@app.get("/test-db")
def test_db():
    """数据库连通性测试：验证 FastAPI -> PyMySQL -> MySQL 链路。"""
    try:
        connection = get_connection()
    except Exception as exc:
        return {"status": "error", "message": f"connect failed: {exc}"}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version, DATABASE() AS db")
            row = cursor.fetchone()
        return {
            "status": "ok",
            "database": "connected",
            "mysql_version": row["version"],
            "db_name": row["db"],
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
    finally:
        connection.close()
