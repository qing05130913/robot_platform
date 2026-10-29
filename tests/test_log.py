"""登录日志接口测试。

本文件只涉及 login_logs（登录日志）。登录日志数据由本模块的 login_logs_data
fixture 自行产生，不依赖其他测试。operation_logs（设备操作日志）见 test_device.py。
"""
import uuid

import pytest

from common.assertions import (
    CODE_UNAUTHORIZED,
    CODE_USER_NOT_FOUND,
    assert_biz_error,
    assert_success,
)

USERNAMES = ["alice", "bob", "admin"]


@pytest.fixture(scope="module")
def login_logs_data(api_client):
    """模块级前置：确保 alice / bob 各产生至少一条登录日志。"""
    for username, password in [("alice", "123456"), ("bob", "abcdef")]:
        response = api_client.post("/login", json={"username": username, "password": password})
        assert_success(response)


@pytest.mark.parametrize("username", USERNAMES)
@pytest.mark.permission
def test_get_login_logs(login_logs_data, username, api_client, users):
    user = users[username]

    response = api_client.get("/login-logs", token=f"token_{username}")

    result = assert_success(response)

    if user["role"] != "admin":
        # 普通用户只能看到自己的登录日志
        for log in result["data"]:
            assert log["user_id"] == user["id"]
    else:
        # admin 看到全部，至少覆盖两名用户
        user_ids = {log["user_id"] for log in result["data"] if log["user_id"] is not None}
        assert len(user_ids) >= 2


def test_get_login_logs_invalid_token(api_client):
    response = api_client.get("/login-logs", token="token_wrong")

    assert_biz_error(response, 401, CODE_UNAUTHORIZED)


def test_login_logs_records_username_snapshot(api_client, db):
    """登录失败（用户不存在）时，登录日志应记录尝试的用户名快照。"""
    username = f"nosuch_{uuid.uuid4().hex[:8]}"

    try:
        response = api_client.post("/login", json={"username": username, "password": "x"})
        assert_biz_error(response, 401, CODE_USER_NOT_FOUND)

        with db.cursor() as cur:
            cur.execute(
                "SELECT user_id, username, result FROM login_logs WHERE username = %s ORDER BY id DESC",
                (username,),
            )
            rows = cur.fetchall()

        assert rows, "登录日志未记录该用户名的失败尝试"
        assert rows[0]["user_id"] is None
        assert rows[0]["result"] == "failed"
    finally:
        with db.cursor() as cur:
            cur.execute("DELETE FROM login_logs WHERE username = %s", (username,))
