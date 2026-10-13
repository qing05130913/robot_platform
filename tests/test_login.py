import requests
import pytest

from common.api_client import APIClient

client = APIClient()

@pytest.mark.parametrize(
    "username,password,expected_status,expected_code",
    [
        ("alice", "123456", 200, 0),
        ("alice", "wrong", 401, 10002),
        ("xxx", "123456", 401, 10001),
        ("", "123456", 422, None),
        ("alice", "", 422, None),
    ]
)
def test_login(username, password, expected_status, expected_code):

    data = {
        "username": username,
        "password": password
    }

    response = client.post("/login", json=data)

    assert response.status_code == expected_status

    if expected_status != 422:
        result = response.json()

        assert result["code"] == expected_code

        if expected_code == 0:
            assert result["data"]["username"] == username
            assert result["data"]["token"]