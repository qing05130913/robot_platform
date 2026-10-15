"""登录接口测试。"""
import uuid

import pytest


def test_login_success(api_client, users):
    """登录成功：token 为固定格式 token_<username>，user_id / role 与数据库一致。"""
    response = api_client.post("/login", json={"username": "alice", "password": "123456"})

    assert response.status_code == 200
    result = response.json()
    assert result["code"] == 0
    assert result["data"]["token"] == "token_alice"
    assert result["data"]["username"] == "alice"
    assert result["data"]["user_id"] == users["alice"]["id"]
    assert result["data"]["role"] == users["alice"]["role"]


@pytest.mark.parametrize(
    "username, password, expected_status, expected_code",
    [
        ("alice", "wrong", 401, 10002),          # 密码错误
        ("nosuchuser", "123456", 401, 10001),    # 用户不存在
        ("", "123456", 422, None),               # 空用户名
        ("alice", "", 422, None),                # 空密码
    ],
)
def test_login_failure(username, password, expected_status, expected_code, api_client):
    response = api_client.post("/login", json={"username": username, "password": password})

    assert response.status_code == expected_status
    if expected_status != 422:
        assert response.json()["code"] == expected_code


@pytest.fixture()
def disabled_user(db):
    """创建一个临时禁用用户，测试后删除。"""
    username = f"disabled_{uuid.uuid4().hex[:8]}"
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password, role, status) VALUES (%s, %s, 'user', 'disabled')",
            (username, "disabled123"),
        )
        user_id = cur.lastrowid

    yield {"username": username, "password": "disabled123", "id": user_id}

    with db.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


def test_login_disabled_user(disabled_user, api_client):
    """被禁用用户即使密码正确也应返回 403 / 10003。"""
    response = api_client.post(
        "/login",
        json={"username": disabled_user["username"], "password": disabled_user["password"]},
    )
    assert response.status_code == 403
    assert response.json()["code"] == 10003
