"""pytest 全局 fixture：集中管理测试共享资源。

设计说明：
- 复用 backend.database.get_connection()，不重复创建数据库配置；
- api_client 无状态，session 级复用；db / users / devices 均为 function 级，
  每次测试解析最新数据，避免使用已被删除或失效的设备 / 用户 ID；
- db 连接用 try/finally 关闭，即使测试异常也不会泄漏连接；
- db 显式开启 autocommit：否则 InnoDB 的 REPEATABLE READ 会在首次 SELECT 时建立
  快照，导致「先读、再通过 API 写入、后回读」读到旧值，使一致性断言失真。
"""
import pytest

from common.api_client import APIClient
from backend.database import get_connection


@pytest.fixture(scope="session")
def api_client():
    """会话级 API 客户端（无状态，可安全复用）。"""
    return APIClient()


@pytest.fixture()
def db():
    """单次测试用的数据库连接，用后可靠关闭。"""
    conn = get_connection()
    conn.autocommit(True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def users(db):
    """按用户名解析种子用户，返回 ``{username: {id, username, role, status}}``。

    主键由数据库动态解析，测试只依赖稳定的业务键 username。
    """
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, role, status FROM users "
            "WHERE username IN ('alice', 'bob', 'admin')"
        )
        rows = cur.fetchall()
    return {row["username"]: row for row in rows}


@pytest.fixture()
def devices(db):
    """按设备名解析种子设备，返回 ``{name: {id, name, owner_id}}``。

    只取不变字段（id/name/owner_id）；status/battery 属可变状态，需要时通过
    db 实时读取，不在这里缓存。
    """
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name, owner_id FROM devices "
            "WHERE name IN ('Robot-A', 'Robot-B', 'Robot-C')"
        )
        rows = cur.fetchall()
    return {row["name"]: row for row in rows}
