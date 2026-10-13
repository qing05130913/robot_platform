import os

import pytest

from config import BASE_URL
from common.api_client import APIClient
from backend.database import get_connection

client = APIClient()

# ============================================================
# 测试数据
# ============================================================

USERS = [
    {"token": "token_alice", "user_id": 1, "role": "user"},
    {"token": "token_bob", "user_id": 2, "role": "user"},
    {"token": "token_admin", "user_id": 3, "role": "admin"},
]

DEVICES = [
    {"device_id": 1, "owner_id": 1},
    {"device_id": 2, "owner_id": 1},
    {"device_id": 3, "owner_id": 2},
]


# ============================================================
# 权限规则
# ============================================================

def expected_permission_status(user, device):
    """
    根据业务规则判断用户是否有权限访问/操作设备。
    """

    if user["role"] == "admin":
        return 200

    if user["user_id"] == device["owner_id"]:
        return 200

    return 403


# ============================================================
# PyMySQL 数据库工具
# ============================================================

def get_operation_log_count():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM operation_logs"
    )

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return result["COUNT(*)"]


def get_latest_operation_log():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id, device_id, action
        FROM operation_logs
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    if result is None:
        return None

    return (result["user_id"], result["device_id"], result["action"])


def get_operation_log_max_id():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT MAX(id) FROM operation_logs")

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    if result["MAX(id)"] is None:
        return 0

    return result["MAX(id)"]


def get_operation_logs_after(log_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT user_id, device_id, action
        FROM operation_logs
        WHERE id > %s
        ORDER BY id
        """,
        (log_id,)
    )

    result = cursor.fetchall()

    cursor.close()
    connection.close()

    return [(row["user_id"], row["device_id"], row["action"]) for row in result]


def get_device_status(device_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT status
        FROM devices
        WHERE id = %s
        """,
        (device_id,)
    )

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    if result is None:
        return None

    return result["status"]


def get_device_battery(device_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT battery
        FROM devices
        WHERE id = %s
        """,
        (device_id,)
    )

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    if result is None:
        return None

    return result["battery"]


def restore_device_status(device_id, status):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE devices
        SET status = %s
        WHERE id = %s
        """,
        (status, device_id)
    )

    connection.commit()

    cursor.close()
    connection.close()


def restore_device_battery(device_id, battery):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE devices
        SET battery = %s
        WHERE id = %s
        """,
        (battery, device_id)
    )

    connection.commit()

    cursor.close()
    connection.close()


# ============================================================
# GET /devices
# ============================================================

@pytest.mark.parametrize(
    "token, expected_status, user_id, role",
    [
        ("token_alice", 200, 1, "user"),
        ("token_bob", 200, 2, "user"),
        ("token_admin", 200, None, "admin"),
        ("token_wrong", 401, None, None),
    ]
)
def test_get_devices(
    token,
    expected_status,
    user_id,
    role
):

    response = client.get(
        "/devices",
        token=token
    )

    assert response.status_code == expected_status

    if expected_status == 200:

        result = response.json()

        assert result["code"] == 0
        assert isinstance(result["data"], list)

        devices = result["data"]

        if role == "admin":
            # 管理员应能看到不同用户的设备（跨属主）
            owner_ids = {device["owner_id"] for device in devices}
            assert len(owner_ids) >= 2
        else:
            # 普通用户只能看到属于自己的设备
            assert devices
            assert all(device["owner_id"] == user_id for device in devices)


# ============================================================
# GET /devices/{device_id}
# 权限测试
# ============================================================

@pytest.mark.parametrize("user", USERS)
@pytest.mark.parametrize("device", DEVICES)
def test_get_device(user, device):

    expected = expected_permission_status(
        user,
        device
    )
    device_id = device["device_id"]

    response = client.get(
        f"/devices/{device_id}",
        token = user["token"]
    )

    assert response.status_code == expected

    if expected == 200:

        result = response.json()

        assert result["code"] == 0
        assert result["data"]["id"] == device_id
        assert result["data"]["owner_id"] == device["owner_id"]


# ============================================================
# GET /devices/{device_id}
# 异常测试
# ============================================================

@pytest.mark.parametrize(
    "token, device_id, expected_status",
    [
        ("token_wrong", 1, 401),
        ("token_wrong", 999, 401),

        ("token_alice", 999, 404),
        ("token_bob", 999, 404),
        ("token_admin", 999, 404),
    ]
)
def test_get_device_abnormal(
    token,
    device_id,
    expected_status
):

    url = f"/devices/{device_id}"

    response = client.get(
        url,
        token=token
    )

    assert response.status_code == expected_status


# ============================================================
# PUT /devices/{device_id}/status
# 权限测试
# ============================================================

@pytest.mark.parametrize("user", USERS)
@pytest.mark.parametrize("device", DEVICES)
def test_update_device_status_permission(user, device):

    expected = expected_permission_status(
        user,
        device
    )

    device_id = device["device_id"]

    url = f"/devices/{device_id}/status"

    # 记录被测设备的原始状态，测试结束后恢复，避免权限测试污染种子设备
    original_status = get_device_status(device_id)

    try:
        response = client.put(
            url,
            token = user["token"],
            json={
                "status": "offline"
            }
        )

        assert response.status_code == expected
    finally:
        # 无论断言是否通过都执行：只要状态被改动就还原。
        # 403/404/422 不会写库，状态未变，不会触发多余的 UPDATE。
        current_status = get_device_status(device_id)
        if original_status is not None and current_status != original_status:
            restore_device_status(device_id, original_status)


# ============================================================
# PUT /devices/{device_id}/status
# 成功业务链 + 数据库一致性
# ============================================================

@pytest.mark.parametrize(
    "token, user_id, device_id, new_status",
    [
        ("token_alice", 1, 1, "offline"),
        ("token_alice", 1, 1, "online"),
        ("token_bob", 2, 3, "offline"),
        ("token_admin", 3, 1, "error"),
    ]
)
def test_update_device_status_success(
    token,
    user_id,
    device_id,
    new_status
):

    # 记录被测设备的原始状态，以及当前日志最大 id 作为本次日志基准
    original_status = get_device_status(device_id)
    max_id_before = get_operation_log_max_id()

    try:
        # PUT
        response = client.put(
            f"/devices/{device_id}/status",
            token=token,
            json={
                "status": new_status
            }
        )

        # HTTP + 业务响应
        assert response.status_code == 200

        result = response.json()

        assert result["code"] == 0
        assert result["data"] is None

        # GET验证设备状态
        response = client.get(
            f"/devices/{device_id}",
            token=token
        )

        assert response.status_code == 200

        result = response.json()

        assert result["code"] == 0
        assert result["data"]["id"] == device_id
        assert result["data"]["status"] == new_status

        # 数据库验证
        db_status = get_device_status(device_id)

        assert db_status == new_status

        # 验证本次请求写入的日志：基准 id 之后应恰好新增一条，且字段匹配
        new_logs = get_operation_logs_after(max_id_before)

        assert len(new_logs) == 1
        assert new_logs[0][0] == user_id
        assert new_logs[0][1] == device_id
        assert new_logs[0][2] == "修改设备状态"
    finally:
        # 恢复设备原始状态；仅当状态确实变化时才恢复，避免多余 UPDATE
        current_status = get_device_status(device_id)
        if original_status is not None and current_status != original_status:
            restore_device_status(device_id, original_status)


# ============================================================
# PUT /devices/{device_id}/status
# 异常测试
# ============================================================

@pytest.mark.parametrize(
    "token, device_id, status_value, expected_status",
    [
        ("token_wrong", 1, "offline", 401),

        ("token_alice", 999, "offline", 404),
        ("token_bob", 999, "offline", 404),
        ("token_admin", 999, "offline", 404),

        ("token_alice", 1, "invalid", 422),
        ("token_alice", 1, "", 422),
    ]
)
def test_update_device_status_abnormal(
    token,
    device_id,
    status_value,
    expected_status
):

    url = f"/devices/{device_id}/status"

    response = client.put(
        url,
        token=token,
        json={
            "status": status_value
        }
    )

    assert response.status_code == expected_status


# ============================================================
# PUT /devices/{device_id}/battery
# 边界值测试
# ============================================================

@pytest.mark.parametrize(
    "token, device_id, battery, expected_status",
    [
        ("token_alice", 1, 0, 200),
        ("token_alice", 1, 1, 200),
        ("token_alice", 1, 99, 200),
        ("token_alice", 1, 100, 200),

        ("token_alice", 1, -1, 422),
        ("token_alice", 1, 101, 422),
        ("token_alice", 1, 50.5, 422),
        ("token_alice", 1, None, 422),
    ]
)
def test_update_device_battery_boundary(
    token,
    device_id,
    battery,
    expected_status
):

    url = f"/devices/{device_id}/battery"
    original_battery = get_device_battery(device_id)
    try:
        response = client.put(
            url,
            token=token,
            json={
                "battery": battery
            }
        )

        assert response.status_code == expected_status

    finally:
        current_battery = get_device_battery(device_id)

        if current_battery != original_battery:
            restore_device_battery(device_id, original_battery)

# ============================================================
# PUT /devices/{device_id}/battery
# 权限测试
# ============================================================

@pytest.mark.parametrize("user", USERS)
@pytest.mark.parametrize("device", DEVICES)
def test_update_device_battery_permission(user, device):

    expected = expected_permission_status(
        user,
        device
    )

    device_id = device["device_id"]

    url = f"/devices/{device_id}/battery"

    # 记录被测设备的原始电量，测试结束后恢复，避免权限测试污染种子设备。
    # 若读取失败（数据库异常）会直接抛出，不会被当作“无需恢复”。
    original_battery = get_device_battery(device_id)

    try:
        response = client.put(
            url,
            token = user["token"],
            json={
                "battery": 50
            }
        )

        assert response.status_code == expected
    finally:
        # 仅当原始电量读取成功（非 None）且当前电量确实变化时才恢复；
        # 403/404/422 不会写库，电量未变，不会触发多余 UPDATE。
        current_battery = get_device_battery(device_id)
        if original_battery is not None and current_battery != original_battery:
            restore_device_battery(device_id, original_battery)


# ============================================================
# PUT /devices/{device_id}/battery
# 成功业务链 + 数据库一致性
# ============================================================

@pytest.mark.parametrize(
    "token, user_id, device_id, new_battery",
    [
        ("token_alice", 1, 1, 0),
        ("token_alice", 1, 1, 100),
        ("token_bob", 2, 3, 50),
        ("token_admin", 3, 1, 80),
        
    ]
)
def test_update_device_battery_success(
    token,
    user_id,
    device_id,
    new_battery
):

    # 记录被测设备的原始电量，以及当前日志最大 id 作为本次日志基准
    original_battery = get_device_battery(device_id)
    max_id_before = get_operation_log_max_id()

    try:
        # PUT修改电量
        response = client.put(
            f"/devices/{device_id}/battery",
            token=token,
            json={
                "battery": new_battery
            }
        )

        # HTTP + 业务响应
        assert response.status_code == 200

        result = response.json()

        assert result["code"] == 0
        assert result["data"] is None

        # GET验证电量
        response = client.get(
            f"/devices/{device_id}",
            token=token
        )

        assert response.status_code == 200

        result = response.json()

        assert result["code"] == 0
        assert result["data"]["id"] == device_id
        assert result["data"]["battery"] == new_battery

        # 数据库验证
        db_battery = get_device_battery(device_id)

        assert db_battery == new_battery

        # 验证本次请求写入的日志：基准 id 之后应恰好新增一条，且字段匹配
        new_logs = get_operation_logs_after(max_id_before)

        assert len(new_logs) == 1
        assert new_logs[0][0] == user_id
        assert new_logs[0][1] == device_id
        assert new_logs[0][2] == "修改设备电量"
    finally:
        # 恢复设备原始电量；仅当电量确实变化时才恢复，避免多余 UPDATE
        current_battery = get_device_battery(device_id)
        if original_battery is not None and current_battery != original_battery:
            restore_device_battery(device_id, original_battery)


# ============================================================
# PUT /devices/{device_id}/battery
# 异常测试
# ============================================================

@pytest.mark.parametrize(
    "token, device_id, battery, expected_status",
    [
        # Token错误
        ("token_wrong", 1, 50, 401),

        # 设备不存在
        ("token_alice", 999, 50, 404),
        ("token_bob", 999, 50, 404),
        ("token_admin", 999, 50, 404),

        # 电量越界
        ("token_alice", 1, -1, 422),
        ("token_alice", 1, 101, 422),
    ]
)
def test_update_device_battery_abnormal(
    token,
    device_id,
    battery,
    expected_status
):

    url = f"/devices/{device_id}/battery"

    response = client.put(
        url,
        token=token,
        json={
            "battery": battery
        }
    )

    assert response.status_code == expected_status
# ============================================================
# GET /operation-logs
# ============================================================

@pytest.mark.parametrize("user", USERS)
def test_get_operation_logs(user):

    response = client.get(
        "/operation-logs",
        token = user["token"]
    )
    assert response.status_code ==200
    result=response.json()
    assert result["code"] == 0

    if user["role"]!="admin":
        for log in result["data"]:
            assert log["user_id"]==user["user_id"]
    else:
        user_ids = {log["user_id"] for log in result["data"]}
        assert len(user_ids) >= 2

def test_get_operation_logs_invalid_token():


    response = client.get(
        "/operation-logs",
        token="token_wrong"
    )

    assert response.status_code == 401

    result = response.json()

    assert result["code"] !=0

# ============================================================
# DELETE /devices/{device-id}
# ============================================================


# 测试不同用户删除设备时的权限
@pytest.mark.parametrize(
    "create_token, delete_token, expected_status",
    [
        # Alice 创建，Alice 删除 → 有权限
        ("token_alice", "token_alice", 200),

        # Alice 创建，Admin 删除 → 有权限
        ("token_alice", "token_admin", 200),

        # Alice 创建，Bob 删除 → 无权限
        ("token_alice", "token_bob", 403),
    ]
)
def test_delete_device_permission(
    create_token,
    delete_token,
    expected_status
):
    
    device_id = None
    try:
        # 先创建一个测试设备
        create_response = client.post(
            "/devices",
            token=create_token,
            json={
                "name": "Robot-Delete-Permission-Test",
                "status": "offline",
                "battery": 80
            }
        )

        assert create_response.status_code == 200

        # 获取刚创建的设备 ID
        device_id = create_response.json()["data"]["id"]

        # 尝试删除设备
        response = client.delete(
            f"/devices/{device_id}",
            token=delete_token
        )

        # 验证 HTTP 状态码
        assert response.status_code == expected_status

        if expected_status == 200:

            # 删除成功后，设备应该不存在
            response = client.get(
                f"/devices/{device_id}",
                token=delete_token
            )

            assert response.status_code == 404

            result = response.json()
            assert result["code"] != 0

        else:

            # 删除失败后，设备应该仍然存在
            response =client.get(
                f"/devices/{device_id}",
                token=create_token
            )

            assert response.status_code == 200

            result = response.json()
            assert result["code"] == 0

    finally:
        if device_id is not None:
            check_response = client.get(
                f"/devices/{device_id}",
                token="token_admin"
            )

            if check_response.status_code == 200:
                cleanup_response = client.delete(
                    f"/devices/{device_id}",
                    token="token_admin"
                )
                assert cleanup_response.status_code == 200

# 测试错误 Token
def test_delete_device_invalid_token():

    response = client.delete(
        "/devices/1",
        token="token_wrong"
    )

    # 错误 Token 应该返回 401
    assert response.status_code == 401


# 测试删除不存在的设备
def test_delete_device_not_found():

    response = client.delete(
        "/devices/99999",
        token="token_admin"
    )

    # 不存在的设备应该返回 404
    assert response.status_code == 404

    result = response.json()
    assert result["code"] != 0

# ============================================================
# POST /devices
# ============================================================


# 正常创建设备
# Alice、Bob、Admin 都应该可以创建
@pytest.mark.parametrize(
    "token, owner_id, device_name",
    [
        ("token_alice", 1, "Robot-Test-A"),
        ("token_bob", 2, "Robot-Test-B"),
        ("token_admin", 3, "Robot-Test-Admin"),
    ]
)
def test_create_device(token, owner_id, device_name):

    device_id=None
    try:
        # POST 请求创建设备
        response = client.post(
            "/devices",
            token=token,
            json={
                "name": device_name,
                "status": "offline",
                "battery": 80
            }
        )

        # 验证创建成功
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == 0

        # 获取新创建的设备 ID
        device_id = result["data"]["id"]

        # 创建成功后，通过 GET 查询设备
        response = client.get(
            f"/devices/{device_id}",
            token=token
        )

        # 验证查询成功
        assert response.status_code == 200

        result = response.json()
        data = result["data"]

        # 验证设备信息
        assert data["name"] == device_name
        assert data["owner_id"] == owner_id
        assert data["status"] == "offline"
        assert data["battery"] == 80

    finally:
        if device_id is not None:
            cleanup_response = client.delete(
                f"/devices/{device_id}",
                token="token_admin"
            )
            assert cleanup_response.status_code in (200, 404)


# 测试错误 Token 不能创建设备
def test_create_device_invalid_token():

    response = client.post(
        "/devices",
        token="token_wrong",
        json={
            "name": "Robot-Test-Wrong",
            "status": "offline",
            "battery": 80
        }
    )

    # 错误 Token 应该返回 401
    assert response.status_code == 401


# 测试重复设备名称
def test_create_device_duplicate_name():
    device_id=None
    device_name = "Robot-Duplicate"
    try:
        # 先创建一个设备，准备重复名称的测试数据
        response = client.post(
            "/devices",
            token="token_alice",
            json={
                "name": device_name,
                "status": "offline",
                "battery": 80
            }
        )

        # 确保前置设备创建成功
        assert response.status_code == 200

        # 获取第一次创建的设备 ID
        device_id = response.json()["data"]["id"]

        # 再次使用相同名称创建
        response = client.post(
            "/devices",
            token="token_alice",
            json={
                "name": device_name,
                "status": "offline",
                "battery": 80
            }
        )

        # 重复名称应该返回 400
        assert response.status_code == 400

        result = response.json()

        # 验证业务错误码
        assert result["code"] == 400

    finally:
        if device_id is not None:
            cleanup_response = client.delete(
                f"/devices/{device_id}",
                token="token_admin"
            )
            assert cleanup_response.status_code in (200, 404)