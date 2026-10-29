"""登录接口测试。"""
import uuid

import pytest

from common.assertions import (
    CODE_USER_DISABLED,
    CODE_USER_NOT_FOUND,
    CODE_WRONG_PASSWORD,
    assert_biz_error,
    assert_success,
    assert_validation_error,
)


@pytest.mark.smoke
def test_login_success(api_client, users):
    """登录成功：token 为固定格式 token_<username>，user_id / role 与数据库一致。"""
    response = api_client.post("/login", json={"username": "alice", "password": "123456"})

    result = assert_success(response)
    assert result["data"]["token"] == "token_alice"
    assert result["data"]["username"] == "alice"
    assert result["data"]["user_id"] == users["alice"]["id"]
    assert result["data"]["role"] == users["alice"]["role"]


@pytest.mark.parametrize(
    "username, password, expected_status, expected_code",
    [
        ("alice", "wrong", 401, CODE_WRONG_PASSWORD),       # 密码错误
        ("nosuchuser", "123456", 401, CODE_USER_NOT_FOUND),  # 用户不存在
        ("", "123456", 422, None),                # 空用户名
        ("alice", "", 422, None),                 # 空密码
    ],
)
def test_login_failure(username, password, expected_status, expected_code, api_client):
    response = api_client.post("/login", json={"username": username, "password": password})

    if expected_status == 422:
        assert_validation_error(response)
    else:
        assert_biz_error(response, expected_status, expected_code)


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
    assert_biz_error(response, 403, CODE_USER_DISABLED)
