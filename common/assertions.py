"""统一断言层。

把「HTTP 状态码 + 业务 code + 响应结构」的校验收敛到一处，
替代散落各用例的 `assert response.status_code == xxx` + `result["code"] == xxx`。

所有断言函数都返回解析后的 JSON body，调用方直接取 data，省一次重复 parse。
"""
from pydantic import BaseModel, ValidationError

# 业务错误码（与后端 README / routers 保持一致，集中定义避免魔法数字）
CODE_SUCCESS = 0
CODE_USER_NOT_FOUND = 10001   # 用户不存在（登录）
CODE_WRONG_PASSWORD = 10002   # 密码错误
CODE_USER_DISABLED = 10003    # 用户被禁用
CODE_UNAUTHORIZED = 10401     # Token 无效 / 未提供
CODE_FORBIDDEN = 10403        # 无权限
CODE_NOT_FOUND = 10404        # 用户/设备不存在
CODE_DUPLICATE_NAME = 400     # 设备名称已存在（后端复用了 HTTP 400 作业务码）


def _json(response):
    """解析响应体，解析失败时给出友好报错。"""
    try:
        return response.json()
    except ValueError:
        raise AssertionError(f"响应不是合法 JSON：HTTP {response.status_code}")


def assert_success(response, status_code=200):
    """断言成功：状态码匹配 + 业务 code == 0。返回 body。"""
    assert response.status_code == status_code, f"期望 HTTP {status_code}，实际 {response.status_code}"
    body = _json(response)
    assert body["code"] == CODE_SUCCESS, f"期望 code={CODE_SUCCESS}，实际 {body.get('code')!r}"
    return body


def assert_biz_error(response, status_code, code):
    """断言业务错误：状态码 + 业务 code 都匹配。返回 body。"""
    assert response.status_code == status_code, f"期望 HTTP {status_code}，实际 {response.status_code}"
    body = _json(response)
    assert body["code"] == code, f"期望 code={code}，实际 {body.get('code')!r}"
    return body


def assert_validation_error(response):
    """断言 422 参数校验失败。422 响应已统一为 {code, message, data}。"""
    assert response.status_code == 422, f"期望 HTTP 422，实际 {response.status_code}"
    body = _json(response)
    assert body["code"] == 422, f"期望 code=422，实际 {body.get('code')!r}"
    return body


def _assert_model(data, model: type[BaseModel]):
    """用 Pydantic 模型校验一份数据，失败时转成带字段路径的 AssertionError。"""
    try:
        model.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise AssertionError(f"数据不符合 {model.__name__} 契约：{details}") from exc
    return data


def assert_contract(response, model: type[BaseModel]):
    """用后端 Pydantic 模型校验整个响应结构（字段是否齐全、类型是否正确）。

    契约直接复用 backend/schemas 里的响应模型，不另写一份 JSON Schema：
    接口模型是唯一事实来源，后端改了模型，测试侧的契约自动同步。

    只校验「结构」，不校验「取值」——具体值由用例里现有的业务断言负责。
    失败时抛出带字段路径的 AssertionError，一眼看出是哪个字段被删/改了类型。
    """
    return _assert_model(_json(response), model)

