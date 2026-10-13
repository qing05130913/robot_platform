"""管理员后台统计数据服务。"""
from database import get_connection


def get_statistics() -> dict:
    """统计用户数、设备数、在线/离线设备数与平均电量。

    所有统计直接基于数据库实时计算，不写死任何数值。
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM users) AS user_count, "
                "(SELECT COUNT(*) FROM devices) AS device_count, "
                "(SELECT COUNT(*) FROM devices WHERE status = 'online') AS online_count, "
                "(SELECT COUNT(*) FROM devices WHERE status = 'offline') AS offline_count, "
                "(SELECT AVG(battery) FROM devices) AS average_battery"
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    average_battery = row["average_battery"]
    return {
        "user_count": row["user_count"],
        "device_count": row["device_count"],
        "online_count": row["online_count"],
        "offline_count": row["offline_count"],
        "average_battery": float(average_battery) if average_battery is not None else 0.0,
    }
