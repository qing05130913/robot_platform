"""设备接口测试。

- 权限矩阵通过 username × device_name 参数化，主键由 conftest 的 users/devices
  fixture 动态解析，不硬编码自增 ID；
- 数据库校验统一走 conftest 的 db fixture（autocommit 连接 + 游标上下文管理器），
  避免连接泄漏和「读到旧快照」；
- 创建的临时设备名带 UUID 后缀，清理用 try/finally，保证失败也能还原；
- 操作日志列表的权限测试由测试自身造数并验证其出现在结果中，不依赖其他测试。
"""
import uuid

import pytest


USERNAMES = ["alice", "bob", "admin"]
DEVICE_NAMES = ["Robot-A", "Robot-B", "Robot-C"]
NONEXISTENT_ID = 999999  # 「必然不存在」的哨兵值，用于 404 用例


def expected_permission_status(user: dict, device: dict) -> int:
    """测试侧权限 oracle：admin 任意；普通用户仅自己的设备。"""
    if user["role"] == "admin":
        return 200
    if user["id"] == device["owner_id"]:
        return 200
    return 403


# ============================================================
# 数据库辅助函数（统一用 db fixture，游标由 with 自动关闭）
# ============================================================

def _device_status(db, device_id):
    with db.cursor() as cur:
        cur.execute("SELECT status FROM devices WHERE id = %s", (device_id,))
        row = cur.fetchone()
    return row["status"] if row else None


def _device_battery(db, device_id):
    with db.cursor() as cur:
        cur.execute("SELECT battery FROM devices WHERE id = %s", (device_id,))
        row = cur.fetchone()
    return row["battery"] if row else None


def _restore_device_status(db, device_id, status):
    with db.cursor() as cur:
        cur.execute("UPDATE devices SET status = %s WHERE id = %s", (status, device_id))


def _restore_device_battery(db, device_id, battery):
    with db.cursor() as cur:
        cur.execute("UPDATE devices SET battery = %s WHERE id = %s", (battery, device_id))


def _operation_log_max_id(db):
    with db.cursor() as cur:
        cur.execute("SELECT MAX(id) AS m FROM operation_logs")
        row = cur.fetchone()
    return row["m"] or 0


def _operation_logs_after(db, log_id):
    with db.cursor() as cur:
        cur.execute(
            "SELECT user_id, device_id, action FROM operation_logs "
            "WHERE id > %s ORDER BY id",
            (log_id,),
        )
        rows = cur.fetchall()
    return [(r["user_id"], r["device_id"], r["action"]) for r in rows]


# ============================================================
# GET /devices —— 设备列表
# ============================================================

@pytest.mark.parametrize(
    "token, expected_status, expected_owner",
    [
        ("token_alice", 200, "alice"),
        ("token_bob", 200, "bob"),
        ("token_admin", 200, None),  # admin 看全部
        ("token_wrong", 401, None),
    ],
)
def test_get_devices(token, expected_status, expected_owner, api_client, users):
    response = api_client.get("/devices", token=token)

    assert response.status_code == expected_status

    if expected_status == 200:
        result = response.json()
        assert result["code"] == 0
        assert isinstance(result["data"], list)

        devices = result["data"]
        if expected_owner is None:
            # admin 应能跨属主看到多个用户的设备
            owner_ids = {d["owner_id"] for d in devices}
            assert len(owner_ids) >= 2
        else:
            owner_id = users[expected_owner]["id"]
            assert devices
            assert all(d["owner_id"] == owner_id for d in devices)


# ============================================================
# GET /devices/{device_id} —— 权限矩阵 + 异常
# ============================================================

@pytest.mark.parametrize("username", USERNAMES)
@pytest.mark.parametrize("device_name", DEVICE_NAMES)
def test_get_device(username, device_name, api_client, users, devices):
    user = users[username]
    device = devices[device_name]

    response = api_client.get(f"/devices/{device['id']}", token=f"token_{username}")

    expected = expected_permission_status(user, device)
    assert response.status_code == expected

    if expected == 200:
        result = response.json()
        assert result["code"] == 0
        assert result["data"]["id"] == device["id"]
        assert result["data"]["owner_id"] == device["owner_id"]


@pytest.mark.parametrize(
    "token, device_ref, expected_status",
    [
        ("token_wrong", "Robot-A", 401),  # 无 token：鉴权先于设备存在性
        ("token_wrong", None, 401),
        ("token_alice", None, 404),       # 设备不存在
        ("token_bob", None, 404),
        ("token_admin", None, 404),
    ],
)
def test_get_device_abnormal(token, device_ref, expected_status, api_client, devices):
    device_id = devices[device_ref]["id"] if device_ref else NONEXISTENT_ID
    response = api_client.get(f"/devices/{device_id}", token=token)
    assert response.status_code == expected_status


# ============================================================
# PUT /devices/{device_id}/status
# ============================================================

@pytest.mark.parametrize("username", USERNAMES)
@pytest.mark.parametrize("device_name", DEVICE_NAMES)
def test_update_device_status_permission(username, device_name, api_client, users, devices, db):
    user = users[username]
    device = devices[device_name]
    device_id = device["id"]

    original_status = _device_status(db, device_id)
    try:
        response = api_client.put(
            f"/devices/{device_id}/status",
            token=f"token_{username}",
            json={"status": "offline"},
        )
        assert response.status_code == expected_permission_status(user, device)
    finally:
        current = _device_status(db, device_id)
        if original_status is not None and current != original_status:
            _restore_device_status(db, device_id, original_status)


@pytest.mark.parametrize(
    "username, device_name, new_status",
    [
        ("alice", "Robot-A", "offline"),
        ("alice", "Robot-A", "online"),
        ("bob", "Robot-C", "offline"),
        ("admin", "Robot-A", "error"),
    ],
)
def test_update_device_status_success(username, device_name, new_status, api_client, users, devices, db):
    user = users[username]
    device_id = devices[device_name]["id"]

    original_status = _device_status(db, device_id)
    max_id_before = _operation_log_max_id(db)

    try:
        response = api_client.put(
            f"/devices/{device_id}/status",
            token=f"token_{username}",
            json={"status": new_status},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert result["data"] is None

        # GET 回读
        response = api_client.get(f"/devices/{device_id}", token=f"token_{username}")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == new_status

        # DB 直查
        assert _device_status(db, device_id) == new_status

        # 操作日志：基准 id 之后应恰好新增一条，且字段匹配
        new_logs = _operation_logs_after(db, max_id_before)
        assert len(new_logs) == 1
        assert new_logs[0] == (user["id"], device_id, "修改设备状态")
    finally:
        current = _device_status(db, device_id)
        if original_status is not None and current != original_status:
            _restore_device_status(db, device_id, original_status)


@pytest.mark.parametrize(
    "token, device_ref, status_value, expected_status",
    [
        ("token_wrong", "Robot-A", "offline", 401),
        ("token_alice", None, "offline", 404),
        ("token_bob", None, "offline", 404),
        ("token_admin", None, "offline", 404),
        ("token_alice", "Robot-A", "invalid", 422),
        ("token_alice", "Robot-A", "", 422),
    ],
)
def test_update_device_status_abnormal(token, device_ref, status_value, expected_status, api_client, devices):
    device_id = devices[device_ref]["id"] if device_ref else NONEXISTENT_ID
    response = api_client.put(
        f"/devices/{device_id}/status",
        token=token,
        json={"status": status_value},
    )
    assert response.status_code == expected_status


# ============================================================
# PUT /devices/{device_id}/battery
# ============================================================

@pytest.mark.parametrize(
    "battery, expected_status",
    [
        (0, 200), (1, 200), (99, 200), (100, 200),         # 边界值：合法
        (-1, 422), (101, 422), (50.5, 422), (None, 422),   # 越界 / 类型错误
    ],
)
def test_update_device_battery_boundary(battery, expected_status, api_client, devices, db):
    device_id = devices["Robot-A"]["id"]
    original_battery = _device_battery(db, device_id)

    try:
        response = api_client.put(
            f"/devices/{device_id}/battery",
            token="token_alice",
            json={"battery": battery},
        )
        assert response.status_code == expected_status
    finally:
        current = _device_battery(db, device_id)
        if original_battery is not None and current != original_battery:
            _restore_device_battery(db, device_id, original_battery)


@pytest.mark.parametrize("username", USERNAMES)
@pytest.mark.parametrize("device_name", DEVICE_NAMES)
def test_update_device_battery_permission(username, device_name, api_client, users, devices, db):
    user = users[username]
    device = devices[device_name]
    device_id = device["id"]

    original_battery = _device_battery(db, device_id)
    try:
        response = api_client.put(
            f"/devices/{device_id}/battery",
            token=f"token_{username}",
            json={"battery": 50},
        )
        assert response.status_code == expected_permission_status(user, device)
    finally:
        current = _device_battery(db, device_id)
        if original_battery is not None and current != original_battery:
            _restore_device_battery(db, device_id, original_battery)


@pytest.mark.parametrize(
    "username, device_name, new_battery",
    [
        ("alice", "Robot-A", 0),
        ("alice", "Robot-A", 100),
        ("bob", "Robot-C", 50),
        ("admin", "Robot-A", 80),
    ],
)
def test_update_device_battery_success(username, device_name, new_battery, api_client, users, devices, db):
    user = users[username]
    device_id = devices[device_name]["id"]

    original_battery = _device_battery(db, device_id)
    max_id_before = _operation_log_max_id(db)

    try:
        response = api_client.put(
            f"/devices/{device_id}/battery",
            token=f"token_{username}",
            json={"battery": new_battery},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert result["data"] is None

        # GET 回读
        response = api_client.get(f"/devices/{device_id}", token=f"token_{username}")
        assert response.status_code == 200
        assert response.json()["data"]["battery"] == new_battery

        # DB 直查
        assert _device_battery(db, device_id) == new_battery

        # 操作日志：基准 id 之后应恰好新增一条，且字段匹配
        new_logs = _operation_logs_after(db, max_id_before)
        assert len(new_logs) == 1
        assert new_logs[0] == (user["id"], device_id, "修改设备电量")
    finally:
        current = _device_battery(db, device_id)
        if original_battery is not None and current != original_battery:
            _restore_device_battery(db, device_id, original_battery)


@pytest.mark.parametrize(
    "token, device_ref, battery, expected_status",
    [
        ("token_wrong", "Robot-A", 50, 401),
        ("token_alice", None, 50, 404),
        ("token_bob", None, 50, 404),
        ("token_admin", None, 50, 404),
        ("token_alice", "Robot-A", -1, 422),
        ("token_alice", "Robot-A", 101, 422),
    ],
)
def test_update_device_battery_abnormal(token, device_ref, battery, expected_status, api_client, devices):
    device_id = devices[device_ref]["id"] if device_ref else NONEXISTENT_ID
    response = api_client.put(
        f"/devices/{device_id}/battery",
        token=token,
        json={"battery": battery},
    )
    assert response.status_code == expected_status


# ============================================================
# GET /operation-logs
# ============================================================

@pytest.fixture()
def operation_log_marker(db, users, devices):
    """为 /operation-logs 权限测试准备两条不同用户的操作日志，返回唯一标记。

    该用例只验证「列表接口的权限过滤」，不验证日志产生逻辑（后者由 status/battery
    的成功用例覆盖），因此直接向 operation_logs 造数并带唯一标记，测试结束删除。
    """
    alice_id = users["alice"]["id"]
    bob_id = users["bob"]["id"]
    device_id = devices["Robot-A"]["id"]
    marker = f"权限测试-{uuid.uuid4().hex[:8]}"

    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO operation_logs (user_id, device_id, action) VALUES (%s, %s, %s), (%s, %s, %s)",
            (alice_id, device_id, marker, bob_id, device_id, marker),
        )

    yield marker

    with db.cursor() as cur:
        cur.execute("DELETE FROM operation_logs WHERE action = %s", (marker,))


@pytest.mark.parametrize("username", USERNAMES)
def test_get_operation_logs(operation_log_marker, username, api_client, users):
    user = users[username]
    marker = operation_log_marker

    response = api_client.get("/operation-logs", token=f"token_{username}")

    assert response.status_code == 200
    result = response.json()
    assert result["code"] == 0

    logs = result["data"]
    # 本次测试准备的数据确实出现在返回结果中
    seeded = [log for log in logs if log["action"] == marker]
    assert seeded, "本次准备的操作日志未出现在返回结果中"

    if user["role"] != "admin":
        # 普通用户：只能看到自己的日志
        for log in logs:
            assert log["user_id"] == user["id"]
    else:
        # admin：能看到所有用户，本次准备的 alice + bob 两条日志都可见
        assert {log["user_id"] for log in seeded} == {users["alice"]["id"], users["bob"]["id"]}


def test_get_operation_logs_invalid_token(api_client):
    response = api_client.get("/operation-logs", token="token_wrong")

    assert response.status_code == 401
    assert response.json()["code"] != 0


# ============================================================
# DELETE /devices/{device_id}
# ============================================================

@pytest.mark.parametrize(
    "create_username, delete_username, expected_status",
    [
        ("alice", "alice", 200),  # 属主删除
        ("alice", "admin", 200),  # admin 删除
        ("alice", "bob", 403),    # 非属主删除
    ],
)
def test_delete_device_permission(create_username, delete_username, expected_status, api_client):
    device_id = None
    device_name = f"Robot-Del-{uuid.uuid4().hex[:8]}"

    try:
        create_response = api_client.post(
            "/devices",
            token=f"token_{create_username}",
            json={"name": device_name, "status": "offline", "battery": 80},
        )
        assert create_response.status_code == 200
        device_id = create_response.json()["data"]["id"]

        response = api_client.delete(f"/devices/{device_id}", token=f"token_{delete_username}")
        assert response.status_code == expected_status

        if expected_status == 200:
            check = api_client.get(f"/devices/{device_id}", token=f"token_{delete_username}")
            assert check.status_code == 404
        else:
            check = api_client.get(f"/devices/{device_id}", token=f"token_{create_username}")
            assert check.status_code == 200
    finally:
        if device_id is not None:
            check = api_client.get(f"/devices/{device_id}", token="token_admin")
            if check.status_code == 200:
                cleanup = api_client.delete(f"/devices/{device_id}", token="token_admin")
                assert cleanup.status_code == 200


def test_delete_device_invalid_token(api_client, devices):
    response = api_client.delete(f"/devices/{devices['Robot-A']['id']}", token="token_wrong")
    assert response.status_code == 401


def test_delete_device_not_found(api_client):
    response = api_client.delete(f"/devices/{NONEXISTENT_ID}", token="token_admin")
    assert response.status_code == 404
    assert response.json()["code"] != 0


def test_delete_device_preserves_operation_logs(api_client, users, db):
    """删除设备后，其历史操作日志应保留（device_id 置空、device_name 快照仍在）。"""
    device_name = f"Robot-Del-Log-{uuid.uuid4().hex[:8]}"
    device_id = None

    try:
        # 创建测试设备
        r = api_client.post(
            "/devices",
            token="token_alice",
            json={"name": device_name, "status": "offline", "battery": 80},
        )
        assert r.status_code == 200
        device_id = r.json()["data"]["id"]

        # 修改状态 → 产生一条操作日志（含 device_name 快照）
        r = api_client.put(
            f"/devices/{device_id}/status", token="token_alice", json={"status": "online"}
        )
        assert r.status_code == 200

        # 删除设备
        r = api_client.delete(f"/devices/{device_id}", token="token_alice")
        assert r.status_code == 200

        # 设备已不存在
        r = api_client.get(f"/devices/{device_id}", token="token_alice")
        assert r.status_code == 404

        # 历史日志仍存在：device_id 置空、device_name 快照保留、操作者/动作/时间完整
        with db.cursor() as cur:
            cur.execute(
                "SELECT user_id, device_id, device_name, action, created_at "
                "FROM operation_logs WHERE device_name = %s",
                (device_name,),
            )
            rows = cur.fetchall()
        assert len(rows) == 1
        log = rows[0]
        assert log["device_id"] is None
        assert log["device_name"] == device_name
        assert log["user_id"] == users["alice"]["id"]
        assert log["action"] == "修改设备状态"
        assert log["created_at"] is not None

        # 日志查询接口仍能正常返回（admin 能查到这条 device_id 为空的日志）
        r = api_client.get("/operation-logs", token="token_admin")
        assert r.status_code == 200
        device_names = {x["device_name"] for x in r.json()["data"]}
        assert device_name in device_names
    finally:
        # 清理本测试产生的孤儿日志；设备若未删成功也兜底清理
        with db.cursor() as cur:
            cur.execute("DELETE FROM operation_logs WHERE device_name = %s", (device_name,))
        if device_id is not None:
            check = api_client.get(f"/devices/{device_id}", token="token_admin")
            if check.status_code == 200:
                api_client.delete(f"/devices/{device_id}", token="token_admin")


# ============================================================
# POST /devices
# ============================================================

@pytest.mark.parametrize("username", USERNAMES)
def test_create_device(username, api_client, users):
    device_id = None
    device_name = f"Robot-Test-{username}-{uuid.uuid4().hex[:8]}"

    try:
        response = api_client.post(
            "/devices",
            token=f"token_{username}",
            json={"name": device_name, "status": "offline", "battery": 80},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        device_id = result["data"]["id"]

        # GET 回读并校验设备归属
        response = api_client.get(f"/devices/{device_id}", token=f"token_{username}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == device_name
        assert data["owner_id"] == users[username]["id"]
        assert data["status"] == "offline"
        assert data["battery"] == 80
    finally:
        if device_id is not None:
            cleanup = api_client.delete(f"/devices/{device_id}", token="token_admin")
            assert cleanup.status_code == 200


def test_create_device_invalid_token(api_client):
    response = api_client.post(
        "/devices",
        token="token_wrong",
        json={"name": "Robot-Test-Wrong", "status": "offline", "battery": 80},
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "name, status, battery",
    [
        ("", "offline", 80),                # 空名称
        ("x" * 101, "offline", 80),         # 名称超长（>100）
        ("Robot-Invalid", "invalid", 80),   # 非法状态
        ("Robot-Invalid", "offline", -1),   # 电量越界（<0）
        ("Robot-Invalid", "offline", 101),  # 电量越界（>100）
    ],
)
def test_create_device_validation(name, status, battery, api_client):
    """创建设备参数校验：非法名称/状态/电量应返回 422。"""
    response = api_client.post(
        "/devices",
        token="token_alice",
        json={"name": name, "status": status, "battery": battery},
    )
    assert response.status_code == 422


def test_create_device_duplicate_name(api_client):
    device_id = None
    device_name = f"Robot-Dup-{uuid.uuid4().hex[:8]}"

    try:
        response = api_client.post(
            "/devices",
            token="token_alice",
            json={"name": device_name, "status": "offline", "battery": 80},
        )
        assert response.status_code == 200
        device_id = response.json()["data"]["id"]

        response = api_client.post(
            "/devices",
            token="token_alice",
            json={"name": device_name, "status": "offline", "battery": 80},
        )
        assert response.status_code == 400
        assert response.json()["code"] == 400
    finally:
        if device_id is not None:
            cleanup = api_client.delete(f"/devices/{device_id}", token="token_admin")
            assert cleanup.status_code == 200