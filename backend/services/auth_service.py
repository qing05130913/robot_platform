"""登录认证服务。"""
from database import get_connection
from utils.auth import generate_token


class AuthError(Exception):
    """认证业务异常，携带业务 code 与提示信息。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _record_login_log(user_id, username, result: str) -> None:
    """写入一条登录日志（含用户名快照），时间字段由数据库默认值自动填充。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO login_logs (user_id, username, result) VALUES (%s, %s, %s)",
                (user_id, username, result),
            )
        connection.commit()
    finally:
        connection.close()


def login(username: str, password: str) -> dict:
    """校验用户名密码，成功返回用户基本信息（含 Token）。

    失败时抛出 AuthError，code 与 HTTP 状态码的映射见 routers/auth.py。
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, password, role, status "
                "FROM users WHERE username = %s",
                (username,),
            )
            user = cursor.fetchone()
    finally:
        connection.close()

    if user is None:
        _record_login_log(None, username, "failed")
        raise AuthError(10001, "用户不存在")

    # 当前阶段密码仍为明文存储（第一阶段 test_data.sql），后续接入哈希后再调整。
    if user["password"] != password:
        _record_login_log(user["id"], username, "failed")
        raise AuthError(10002, "密码错误")

    if user["status"] != "active":
        raise AuthError(10003, "用户已被禁用")

    _record_login_log(user["id"], username, "success")

    return {
        "token": generate_token(user["username"]),
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }
