"""设备相关业务服务。

设备的更新操作会同时写入操作日志，且在同一事务中提交，保证两者同时生效。
"""
from typing import Optional

from database import get_connection


def _row_to_device(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "owner_id": row["owner_id"],
        "status": row["status"],
        "battery": row["battery"],
    }


def list_devices(owner_id: Optional[int] = None) -> list:
    """获取设备列表；owner_id 为 None 时返回全部（admin 用）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    "SELECT id, name, owner_id, status, battery FROM devices ORDER BY id"
                )
            else:
                cursor.execute(
                    "SELECT id, name, owner_id, status, battery FROM devices "
                    "WHERE owner_id = %s ORDER BY id",
                    (owner_id,),
                )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return [_row_to_device(row) for row in rows]


def get_device(device_id: int) -> Optional[dict]:
    """根据 ID 查询设备，不存在返回 None。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, owner_id, status, battery FROM devices WHERE id = %s",
                (device_id,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    return _row_to_device(row) if row else None


def get_device_by_name(name: str) -> Optional[dict]:
    """根据名称查询设备，不存在返回 None。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, owner_id, status, battery FROM devices WHERE name = %s",
                (name,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    return _row_to_device(row) if row else None


def update_device_status(device_id: int, status: str, user_id: int) -> None:
    """修改设备状态，并写入一条操作日志（同一事务）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE devices SET status = %s WHERE id = %s",
                (status, device_id),
            )
            cursor.execute(
                "INSERT INTO operation_logs (user_id, device_id, action) VALUES (%s, %s, %s)",
                (user_id, device_id, "修改设备状态"),
            )
        connection.commit()
    finally:
        connection.close()


def update_device_battery(device_id: int, battery: int, user_id: int) -> None:
    """修改设备电量，并写入一条操作日志（同一事务）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE devices SET battery = %s WHERE id = %s",
                (battery, device_id),
            )
            cursor.execute(
                "INSERT INTO operation_logs (user_id, device_id, action) VALUES (%s, %s, %s)",
                (user_id, device_id, "修改设备电量"),
            )
        connection.commit()
    finally:
        connection.close()


def create_device(name: str, owner_id: int, status: str, battery: int) -> dict:
    """创建设备并返回创建后的设备信息。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO devices (name, owner_id, status, battery) VALUES (%s, %s, %s, %s)",
                (name, owner_id, status, battery),
            )
            device_id = cursor.lastrowid
        connection.commit()
    finally:
        connection.close()
    return get_device(device_id)


def delete_device(device_id: int) -> None:
    """删除设备，并先删除其操作日志（operation_logs 外键引用 devices）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM operation_logs WHERE device_id = %s",
                (device_id,),
            )
            cursor.execute(
                "DELETE FROM devices WHERE id = %s",
                (device_id,),
            )
        connection.commit()
    finally:
        connection.close()


def list_operation_logs(user_id: Optional[int] = None) -> list:
    """获取操作日志；user_id 为 None 时返回全部（admin 用）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            if user_id is None:
                cursor.execute(
                    "SELECT id, user_id, device_id, action, created_at "
                    "FROM operation_logs ORDER BY id DESC"
                )
            else:
                cursor.execute(
                    "SELECT id, user_id, device_id, action, created_at "
                    "FROM operation_logs WHERE user_id = %s ORDER BY id DESC",
                    (user_id,),
                )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "device_id": row["device_id"],
            "action": row["action"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
