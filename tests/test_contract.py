"""契约守卫自身的负向证明。

这些用例不依赖后端服务：它们直接构造响应体，验证「字段缺失 / 类型变化时，
assert_contract 一定报错」，从而证明业务用例里的契约断言不是摆设。
"""
import pytest

from backend.schemas.device import DeviceResponse
from common.assertions import assert_contract


class FakeResponse:
    """只实现 assert_contract 用到的最小接口。"""

    def __init__(self, body):
        self._body = body
        self.status_code = 200

    def json(self):
        return self._body


def _valid_body():
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": 1,
            "name": "Robot-X",
            "owner_id": 1,
            "status": "offline",
            "battery": 80,
        },
    }


def test_contract_accepts_valid_response():
    body = _valid_body()
    assert assert_contract(FakeResponse(body), DeviceResponse) == body


def test_contract_rejects_missing_field():
    """模拟后端把 battery 字段删掉（隐性回归），契约守卫必须拦下。"""
    body = _valid_body()
    del body["data"]["battery"]

    with pytest.raises(AssertionError, match="battery"):
        assert_contract(FakeResponse(body), DeviceResponse)


def test_contract_rejects_wrong_type():
    """模拟字段类型被改（int → str），契约守卫必须拦下。"""
    body = _valid_body()
    body["data"]["battery"] = "eighty"

    with pytest.raises(AssertionError, match="battery"):
        assert_contract(FakeResponse(body), DeviceResponse)
