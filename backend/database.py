"""数据库连接配置与连接工厂。

当前采用简单配置方式：通过环境变量读取连接信息，未设置时使用默认值。
真实密码不要写死在代码里，请通过环境变量 DB_PASSWORD 注入。
"""
import os

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "robot_platform"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}


def get_connection():
    """获取一个 MySQL 连接。"""
    return pymysql.connect(**DB_CONFIG)


# 测试数据库与测试模式标识。
# TEST_MODE=1 时，后端启动会校验实际连接库必须是 TEST_DB_NAME，
# 用于防止测试后端误连开发库；日常开发不设置 TEST_MODE，默认连接 robot_platform。
TEST_DB_NAME = "robot_platform_test"
TEST_MODE = os.getenv("TEST_MODE") in ("1", "true", "True")


def assert_test_database() -> None:
    """测试模式安全校验：实际连接库必须是 robot_platform_test，否则抛错拒绝启动。

    日常开发（未设置 TEST_MODE）不做校验，仍默认连接 robot_platform。
    """
    if not TEST_MODE:
        return
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            row = cursor.fetchone()
        actual = row["DATABASE()"] if row else None
    finally:
        connection.close()
    if actual != TEST_DB_NAME:
        raise RuntimeError(
            f"[测试模式] 后端要求连接 {TEST_DB_NAME}，实际连接 {actual!r}。"
            f"请设置 DB_NAME={TEST_DB_NAME} 后再启动测试后端。"
        )
