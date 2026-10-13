import requests
import pytest

from common.api_client import APIClient

client = APIClient()
USERS = [
    {"token": "token_alice", "user_id": 1, "role": "user"},
    {"token": "token_bob", "user_id": 2, "role": "user"},
    {"token": "token_admin", "user_id": 3, "role": "admin"},
]


@pytest.fixture(scope="module")
def login_logs_data():
    # Alice 登录一次
    response = client.post(
        "/login",
        json={
            "username": "alice",
            "password": "123456"
        }
    )
    assert response.status_code == 200

    # Bob 登录一次
    response = client.post(
        "/login",
        json={
            "username": "bob",
            "password": "abcdef"
        }
    )
    assert response.status_code == 200


@pytest.mark.parametrize("user", USERS)
def test_get_login_logs(login_logs_data, user):

    response = client.get("/login-logs",
                          token=user['token'])

    assert response.status_code == 200

    result = response.json()
    assert result["code"] == 0

    if user["role"] != "admin":
        for log in result["data"]:
            assert log["user_id"] == user["user_id"]
    else:
        user_ids = {
            log["user_id"]
            for log in result["data"]
            if log["user_id"] is not None
        }
        assert len(user_ids) >= 2


def test_get_login_logs_invalid_token():

    response =client.get("/login-logs", 
                           token="token_wrong")

    assert response.status_code == 401

    result = response.json()
    assert result["code"] != 0