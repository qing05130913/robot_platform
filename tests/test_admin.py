"""管理员接口测试。"""
import pytest

from backend.database import get_connection
from common.api_client import APIClient
from common.assertions import (
    CODE_FORBIDDEN,
    CODE_UNAUTHORIZED,
    assert_biz_error,
    assert_success,
)

client = APIClient()


def _get_db_statistics():
    """独立查询数据库，计算统计接口的预期值（不依赖接口响应）。"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS c FROM users")
            user_count = cursor.fetchone()["c"]

            cursor.execute("SELECT status, battery FROM devices")
            rows = cursor.fetchall()
    finally:
        connection.close()

    online_count = 0
    offline_count = 0
    batteries = []
    for row in rows:
        if row["status"] == "online":
            online_count += 1
        elif row["status"] == "offline":
            offline_count += 1
        batteries.append(row["battery"])

    # 与后端 AVG(battery)（整数参数，保留 4 位小数）的舍入规则保持一致
    average_battery = round(sum(batteries) / len(batteries), 4) if batteries else 0.0

    return {
        "user_count": user_count,
        "device_count": len(rows),
        "online_count": online_count,
        "offline_count": offline_count,
        "average_battery": average_battery,
    }


def _expected_error_code(status):
    """403/401 对应的业务 code。"""
    return CODE_FORBIDDEN if status == 403 else CODE_UNAUTHORIZED


@pytest.mark.parametrize(
    "token, expected_status",
    [
        ("token_admin", 200),
        ("token_alice", 403),
        ("token_wrong", 401),
    ],
)
def test_admin_get_devices(token, expected_status):
    response = client.get("/admin/devices", token=token)

    if expected_status == 200:
        result = assert_success(response)

        device_names = {device["name"] for device in result["data"]}

        # 验证基础种子设备都在，但不要求集合完全相等，
        # 避免其他测试创建/残留的额外设备导致断言失败
        assert {"Robot-A", "Robot-B", "Robot-C"} <= device_names
    else:
        assert_biz_error(response, expected_status, _expected_error_code(expected_status))


@pytest.mark.parametrize(
    "token, expected_status",
    [
        ("token_admin", 200),
        ("token_alice", 403),
        ("token_wrong", 401),
    ],
)
def test_admin_get_statistics(token, expected_status):
    # 成功场景在请求前从数据库独立计算预期值，避免依赖接口响应
    expected = _get_db_statistics() if expected_status == 200 else None

    response = client.get("/admin/statistics", token=token)

    if expected_status == 200:
        result = assert_success(response)

        data = result["data"]

        assert data["user_count"] == expected["user_count"]
        assert data["device_count"] == expected["device_count"]
        assert data["online_count"] == expected["online_count"]
        assert data["offline_count"] == expected["offline_count"]
        assert data["average_battery"] == pytest.approx(expected["average_battery"], abs=0.0001)
    else:
        assert_biz_error(response, expected_status, _expected_error_code(expected_status))
