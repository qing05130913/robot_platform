"""认证相关工具函数。

使用简单固定格式 Token，方便接口自动化测试：
登录成功返回 token_<username>，后续通过 Authorization: Bearer <token> 识别身份。
"""
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.user_service import get_user_by_username

TOKEN_PREFIX = "token_"

# 声明 HTTP Bearer 认证方案，使 Swagger UI 显示 Authorize 按钮。
_bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)


def generate_token(username: str) -> str:
    """根据用户名生成固定格式 Token。"""
    return f"{TOKEN_PREFIX}{username}"


def parse_token(token: str) -> Optional[str]:
    """解析 Token，返回用户名；格式不合法时返回 None。"""
    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    username = token[len(TOKEN_PREFIX):]
    return username or None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
) -> dict:
    """FastAPI 依赖：从 Authorization: Bearer <token> 解析并查询当前用户。

    无 Token、Token 格式错误或对应用户不存在时返回 401。
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail={"code": 10401, "message": "未提供有效 Token"})

    username = parse_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail={"code": 10401, "message": "Token 无效"})

    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": 10401, "message": "Token 无效"})

    return user
