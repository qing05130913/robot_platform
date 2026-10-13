"""登录日志查询服务。"""
from typing import Optional

from database import get_connection


def list_login_logs(user_id: Optional[int] = None) -> list:
    """获取登录日志；user_id 为 None 时返回全部（admin 用）。

    关联 users 表补充用户名，user_id 为 NULL 的日志也能正常返回。
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            if user_id is None:
                cursor.execute(
                    "SELECT l.id, l.user_id, u.username, l.result, l.created_at "
                    "FROM login_logs l "
                    "LEFT JOIN users u ON l.user_id = u.id "
                    "ORDER BY l.id DESC"
                )
            else:
                cursor.execute(
                    "SELECT l.id, l.user_id, u.username, l.result, l.created_at "
                    "FROM login_logs l "
                    "LEFT JOIN users u ON l.user_id = u.id "
                    "WHERE l.user_id = %s "
                    "ORDER BY l.id DESC",
                    (user_id,),
                )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "username": row["username"],
            "result": row["result"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
