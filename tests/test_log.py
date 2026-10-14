"""登录日志接口测试。

本文件只涉及 login_logs（登录日志）。登录日志数据由本模块的 login_logs_data
fixture 自行产生，不依赖其他测试。operation_logs（设备操作日志）见 test_device.py。
"""
import pytest

USERNAMES = ["alice", "bob", "admin"]


@pytest.fixture(scope="module")
def login_logs_data(api_client):
    """模块级前置：确保 alice / bob 各产生至少一条登录日志。"""
    for username, password in [("alice", "123456"), ("bob", "abcdef")]:
        response = api_client.post(
            "/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200


@pytest.mark.parametrize("username", USERNAMES)
def test_get_login_logs(login_logs_data, username, api_client, users):
    user = users[username]

    response = api_client.get("/login-logs", token=f"token_{username}")

    assert response.status_code == 200
    result = response.json()
    assert result["code"] == 0

    if user["role"] != "admin":
        # 普通用户只能看到自己的登录日志
        for log in result["data"]:
            assert log["user_id"] == user["id"]
    else:
        # admin 看到全部，至少覆盖两名用户
        user_ids = {
            log["user_id"] for log in result["data"] if log["user_id"] is not None
        }
        assert len(user_ids) >= 2


def test_get_login_logs_invalid_token(api_client):
    response = api_client.get("/login-logs", token="token_wrong")

    assert response.status_code == 401
    result = response.json()
    assert result["code"] != 0
