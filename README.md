# Robot Platform Backend

机器人管理平台后端服务（第四阶段：设备模块）。

## 项目结构

```text
backend-demo/
│
├── backend/
│   ├── main.py                 # FastAPI 应用入口，注册路由并统一异常响应格式
│   ├── database.py             # MySQL 连接配置与连接工厂
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # 登录接口路由
│   │   ├── users.py            # 用户接口路由
│   │   └── devices.py          # 设备接口路由
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py             # 登录请求/响应模型
│   │   ├── user.py             # 用户响应模型
│   │   └── device.py           # 设备请求/响应模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py     # 登录业务逻辑
│   │   ├── user_service.py     # 用户查询业务逻辑
│   │   └── device_service.py   # 设备查询/更新、操作日志业务逻辑
│   └── utils/
│       ├── __init__.py
│       └── auth.py             # Token 生成/解析、当前用户依赖
│
├── sql/
│   ├── init.sql                    # 创建数据库及核心表
│   ├── test_data.sql               # 基础测试数据
│   └── migrate_device_module.sql   # 设备模块表结构迁移（已初始化数据库使用）
│
├── requirements.txt            # Python 依赖
└── README.md
```

## 依赖

- Python 3.10+
- MySQL 5.7+ / 8.0
- FastAPI + Uvicorn + PyMySQL

## 安装依赖

```bash
pip install -r requirements.txt
```

## 数据库配置

连接配置通过环境变量读取（`backend/database.py`），真实密码不要写死在代码里：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_HOST` | `127.0.0.1` | 数据库地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `DB_USER` | `root` | 数据库用户名 |
| `DB_PASSWORD` | （空） | 数据库密码 |
| `DB_NAME` | `robot_platform` | 数据库名 |

PowerShell 示例：

```powershell
$env:DB_PASSWORD = "你的MySQL密码"
```

## 初始化 MySQL

首次初始化：

```bash
mysql -u root -p < sql/init.sql
mysql -u root -p < sql/test_data.sql
```

如果数据库已按上一阶段初始化过，执行迁移脚本重建设备相关表即可（保留 users 与 login_logs）：

```bash
mysql -u root -p < sql/migrate_device_module.sql
```

## 启动 FastAPI

在项目根目录下执行：

```bash
cd backend
uvicorn main:app --reload
```

## 认证方式

Token 采用固定格式 `token_<username>`，请求时携带：

```http
Authorization: Bearer token_alice
```

## 接口说明

### 认证 / 用户

- `POST /login` — 登录
- `GET /user` — 当前登录用户信息
- `GET /users/{user_id}` — 查询指定用户（admin 任意，user 仅自己）
- `GET /users` — 用户列表（仅 admin）

### 设备

- `GET /devices` — 设备列表（admin 全部，user 仅自己）
- `GET /devices/{device_id}` — 设备详情（admin 任意，user 仅自己）
- `PUT /devices/{device_id}/status` — 修改状态，`status` 取值 `online` / `offline` / `error`
- `PUT /devices/{device_id}/battery` — 修改电量，`battery` 取值 0-100 的整数
- `GET /operation-logs` — 操作日志（admin 全部，user 仅自己）

## 业务错误码

| code | 含义 | HTTP 状态码 |
| --- | --- | --- |
| 0 | 成功 | 200 |
| 10001 | 用户不存在（登录） | 401 |
| 10002 | 密码错误 | 401 |
| 10003 | 用户被禁用 | 403 |
| 10401 | 未提供 Token / Token 无效 | 401 |
| 10403 | 无权限访问 | 403 |
| 10404 | 用户/设备不存在 | 404 |

## 验证

- 服务运行：浏览器访问 http://127.0.0.1:8000/ ，返回 JSON 即正常。
- 接口文档（Swagger）：http://127.0.0.1:8000/docs
- 数据库连通性：访问 http://127.0.0.1:8000/test-db
- 认证：点击右上角 **Authorize**，Value 处填入 Token（如 `token_alice`），点击 **Authorize** 后，受保护接口会自动携带 `Authorization: Bearer token_alice`。

Git version control is enabled for this project.
