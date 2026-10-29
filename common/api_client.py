import logging

import requests

import common.logger
from config import BASE_URL, TIMEOUT

logger = logging.getLogger(__name__)

# 响应体日志最大长度，超长截断，避免刷爆日志文件
_MAX_BODY_LOG_LEN = 1000
# 请求体里需要脱敏的字段（不区分大小写，命中打码）
_SENSITIVE_KEYS = ("password",)


def _mask(data):
    """脱敏请求体里的敏感字段（如 password），避免密码进日志。"""
    if not isinstance(data, dict):
        return data
    return {k: ("***" if k.lower() in _SENSITIVE_KEYS else v) for k, v in data.items()}


def _truncate(text, limit=_MAX_BODY_LOG_LEN):
    """截断过长的响应体。"""
    if not text:
        return text
    return text if len(text) <= limit else text[:limit] + f"…(截断，共 {len(text)} 字符)"


class APIClient:

    def __init__(self, base_url=BASE_URL):
        # 保存后端基础地址
        self.base_url = base_url

    def _request(self, method, path, **kwargs):
        # 统一处理 Token 并发送 HTTP 请求
        token = kwargs.pop("token", None)
        timeout = kwargs.pop("timeout", TIMEOUT)
        url = f"{self.base_url}{path}"
        if token:
            # 将 Token 转换成 Authorization 请求头
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers

        # 记录请求（脱敏敏感字段）
        body = _mask(kwargs.get("json"))
        logger.info("发送请求：%s %s body=%s", method, url, body)

        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException:
            logger.exception("请求失败：%s %s body=%s", method, url, body)
            raise

        # 记录响应（截断过长 body；非 2xx 用 WARNING，便于一眼定位失败接口）
        resp_body = _truncate(response.text)
        if response.ok:
            logger.info("收到响应：HTTP %s body=%s", response.status_code, resp_body)
        else:
            logger.warning("收到响应：HTTP %s body=%s", response.status_code, resp_body)
        return response

    def get(self, path, **kwargs):
        # 发送 GET 请求
        return self._request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        # 发送 POST 请求
        return self._request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        # 发送 PUT 请求
        return self._request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        # 发送 DELETE 请求
        return self._request("DELETE", path, **kwargs)
