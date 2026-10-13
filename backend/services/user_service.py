"""用户相关业务服务。

所有查询均返回给前端的安全字段（不含密码），并使用参数化 SQL。
"""
from typing import Optional

from database import get_connection


def _row_to_user(row) -> dict:
    """将查询行转换为前端用户结构（不含密码）。"""
    return {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "status": row["status"],
    }


def get_user_by_username(username: str) -> Optional[dict]:
    """根据用户名查询用户（不含密码），不存在返回 None。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, status FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """根据 ID 查询用户（不含密码），不存在返回 None。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, status FROM users WHERE id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    return _row_to_user(row) if row else None


def list_users() -> list:
    """查询全部用户列表（不含密码）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username, role, status FROM users ORDER BY id")
            rows = cursor.fetchall()
    finally:
        connection.close()
    return [_row_to_user(row) for row in rows]
