import requests
from config import BASE_URL,TIMEOUT
import logging
import common.logger

logger = logging.getLogger(__name__)
class APIClient:

    def __init__(self, base_url=BASE_URL):
        # 保存后端基础地址
        self.base_url = base_url

    def _request(self, method, path, **kwargs):
        # 统一处理 Token 并发送 HTTP 请求
        token = kwargs.pop("token", None)
        timeout=kwargs.pop("timeout",TIMEOUT)
        url=f"{self.base_url}{path}"
        if token:
            # 将 Token 转换成 Authorization 请求头
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers

        # 发送实际的 HTTP 请求
        logger.info("发送请求：%s %s",method,url)

        try:
            response = requests.request(
                method,
                url,
                timeout=timeout,
                **kwargs
                )
        except requests.RequestException:
              logger.exception("请求失败：%s %s", method, url)
              raise

        logger.info("收到响应：HTTP %s", response.status_code)
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