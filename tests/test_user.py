import requests
import pytest

from common.api_client import APIClient

client = APIClient()

# =========================
# 测试数据
# =========================

USERS = [
    {"username": "alice", "user_id": 1, "role": "user"},
    {"username": "bob", "user_id": 2, "role": "user"},
    {"username": "admin", "user_id": 3, "role": "admin"},
]


# =========================
# 测试侧权限规则
# =========================

def expected_user_access_status(current_user, target_user_id):
    """
    测试侧业务规则：
    admin 可以访问任意用户；
    普通用户只能访问自己的信息。
    """

    if current_user["role"] == "admin":
        return 200

    if current_user["user_id"] == target_user_id:
        return 200

    return 403

def expected_list_users_status(user):
    if user["role"]=="admin":
        return 200
    return 403


# =========================
# GET /user
# =========================

@pytest.mark.parametrize(
    "token, expected_status, expected_user_id, expected_username",
    [
        ("token_alice", 200, 1, "alice"),
        ("token_bob", 200, 2, "bob"),
        ("token_wrong", 401, None, None),
        ("token_nobody", 401, None, None),
    ]
)
def test_get_current_user(token, expected_status, expected_user_id, expected_username):

    response = client.get("/user",
                            token=token)

    assert response.status_code == expected_status

    if response.status_code == 200:
        result = response.json()

        assert result["code"] == 0
        assert result["data"]["user_id"] == expected_user_id
        assert result["data"]["username"] == expected_username


# =========================
# GET /users/{user_id}
# 权限矩阵自动生成
# =========================

@pytest.mark.parametrize("current_user", USERS)
@pytest.mark.parametrize("target_user_id", [1, 2, 3])
def test_get_user_permission(current_user, target_user_id):

    token = f"token_{current_user['username']}"


    response = client.get(f"/users/{target_user_id}", 
                          token = f"token_{current_user['username']}")

    expected_status = expected_user_access_status(
        current_user,
        target_user_id
    )

    assert response.status_code == expected_status

    if response.status_code == 200:
        result = response.json()

        assert result["code"] == 0
        assert result["data"]["user_id"] == target_user_id


# =========================
# 不存在的用户
# =========================

def test_get_nonexistent_user():

    response = client.get("/users/999",
                             token="token_admin")

    assert response.status_code == 404


@pytest.mark.parametrize("current_user", USERS)
def test_get_users(current_user):
    
    response = client.get("/users", 
                            token = f"token_{current_user['username']}")
    expected_status=expected_list_users_status(current_user)
    assert response.status_code == expected_status

    if response.status_code == 200:
        result = response.json()

        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

        if current_user["role"] == "admin":
            user_ids = {user["user_id"] for user in result["data"]}
            expected_user_ids = {user["user_id"] for user in USERS}
            assert user_ids == expected_user_ids