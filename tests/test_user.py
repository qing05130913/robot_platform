"""用户接口测试。

权限矩阵通过 username（业务键）参数化，主键由 conftest 的 users fixture
在运行时从数据库解析，不硬编码自增 ID。
"""
import pytest

from backend.schemas.user import UserListResponse, UserResponse
from common.assertions import (
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_UNAUTHORIZED,
    assert_biz_error,
    assert_contract,
    assert_success,
)

# 只保留业务键；user_id / role / status 由 conftest.users 动态解析。
USERNAMES = ["alice", "bob", "admin"]


def expected_user_access_status(current_user: dict, target_user_id: int) -> int:
    """测试侧权限 oracle：admin 任意；普通用户仅自己。"""
    if current_user["role"] == "admin":
        return 200
    if current_user["id"] == target_user_id:
        return 200
    return 403


def expected_list_users_status(user: dict) -> int:
    return 200 if user["role"] == "admin" else 403


# =========================
# GET /user —— 当前登录用户信息
# =========================

@pytest.mark.parametrize("username", ["alice", "bob"])
@pytest.mark.smoke
def test_get_current_user(username, api_client, users):
    user = users[username]

    response = api_client.get("/user", token=f"token_{username}")

    result = assert_success(response)
    assert_contract(response, UserResponse)
    assert result["data"]["user_id"] == user["id"]
    assert result["data"]["username"] == username


@pytest.mark.parametrize("token", ["token_wrong", "token_nobody"])
def test_get_current_user_invalid_token(token, api_client):
    response = api_client.get("/user", token=token)
    assert_biz_error(response, 401, CODE_UNAUTHORIZED)


# =========================
# GET /users/{user_id} —— 权限矩阵（3 用户 × 3 目标）
# =========================

@pytest.mark.parametrize("username", USERNAMES)
@pytest.mark.parametrize("target_username", USERNAMES)
@pytest.mark.permission
def test_get_user_permission(username, target_username, api_client, users):
    current_user = users[username]
    target_user = users[target_username]

    response = api_client.get(f"/users/{target_user['id']}", token=f"token_{username}")

    expected = expected_user_access_status(current_user, target_user["id"])
    if expected == 200:
        result = assert_success(response)
        assert_contract(response, UserResponse)
        assert result["data"]["user_id"] == target_user["id"]
    else:
        assert_biz_error(response, 403, CODE_FORBIDDEN)


# =========================
# 不存在的用户
# =========================

def test_get_nonexistent_user(api_client, users):
    # 用「当前最大用户 ID + 1000」作为必然不存在的哨兵值，避免魔法数字。
    nonexistent_id = max(u["id"] for u in users.values()) + 1000
    response = api_client.get(f"/users/{nonexistent_id}", token="token_admin")
    assert_biz_error(response, 404, CODE_NOT_FOUND)


# =========================
# GET /users —— 仅 admin
# =========================

@pytest.mark.parametrize("username", USERNAMES)
@pytest.mark.permission
def test_get_users(username, api_client, users):
    current_user = users[username]

    response = api_client.get("/users", token=f"token_{username}")

    expected = expected_list_users_status(current_user)
    if expected == 200:
        result = assert_success(response)
        assert_contract(response, UserListResponse)
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

        user_ids = {u["user_id"] for u in result["data"]}
        expected_ids = {u["id"] for u in users.values()}
        assert user_ids == expected_ids
    else:
        assert_biz_error(response, 403, CODE_FORBIDDEN)
