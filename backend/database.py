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
