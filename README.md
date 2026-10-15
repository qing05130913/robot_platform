# Robot Platform 接口自动化测试项目

机器人设备管理平台——一个用于学习接口自动化测试的项目。FastAPI 后端是被测系统（SUT），
测试侧使用 Python + requests + pytest + MySQL + PyMySQL，覆盖正常、异常、边界、权限与数据库一致性场景。

## 项目结构

```text
backend-demo/
│
├── backend/                      # 被测系统（SUT）
│   ├── main.py                   # FastAPI 入口，注册路由 + 统一异常响应
│   ├── database.py               # MySQL 连接配置与连接工厂
│   ├── routers/                  # 路由层
│   │   ├── auth.py               # 登录
│   │   ├── users.py              # 用户
│   │   ├── devices.py            # 设备
│   │   ├── login_logs.py         # 登录日志
│   │   └── admin.py              # 管理员
│   ├── schemas/                  # Pydantic 请求/响应模型
│   ├── services/                 # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── device_service.py
│   │   ├── login_log_service.py
│   │   └── admin_service.py
│   └── utils/
│       └── auth.py               # Token 生成/解析、当前用户依赖
│
├── common/                       # 测试公共工具
│   ├── api_client.py             # requests 封装（Token、超时、日志）
│   └── logger.py                 # 日志配置（文件轮转 + 控制台）
│
├── tests/                        # 测试用例
│   ├── conftest.py               # fixture：api_client / db / users / devices
│   ├── test_login.py
│   ├── test_user.py
│   ├── test_device.py
│   ├── test_log.py
│   └── test_admin.py
│
├── sql/                          # 数据库脚本
│   ├── init.sql                  # 建库建表（唯一初始化入口）
│   ├── test_data.sql             # 基础种子数据
│   └── migrate_operation_logs.sql # 旧库升级（保留历史日志）
│
├── config.py                     # 测试侧环境变量（BASE_URL / TIMEOUT）
├── pytest.ini                    # pytest 配置
├── requirements.txt              # 依赖
├── .env.example                  # 环境变量示例（不含真实密码）
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

从零初始化（`init.sql` 是唯一入口，主键统一为 INT）：

```bash
mysql -u root -p < sql/init.sql
mysql -u root -p < sql/test_data.sql
```

若已存在旧库，且 `operation_logs` 尚无 `device_name` 列 / `device_id` 不可空，
执行一次迁移即可（不删除任何数据）：

```bash
mysql -u root -p robot_platform < sql/migrate_operation_logs.sql
```

## 测试数据库说明

当前**测试与开发共用同一个数据库**（默认 `robot_platform`，由环境变量 `DB_NAME` 决定）。
测试会创建/删除临时设备、写入操作日志与登录日志，因此：

- 首次请用 `sql/init.sql` + `sql/test_data.sql` 初始化一个干净库；
- 多次运行会累积 `operation_logs` / `login_logs`（日志为 append-only，测试不做全表清理）；
- 若需隔离，可将 `DB_NAME` 改为独立测试库（如 `robot_platform_test`）并在其上执行初始化脚本。

## 启动 FastAPI

在项目根目录下执行：

```bash
cd backend
uvicorn main:app --reload
```

## 运行测试

先在一个终端启动后端（见上），然后在另一个终端、项目根目录下执行：

```bash
# 运行单个测试用例
python -m pytest tests/test_login.py::test_login_success -v

# 运行单个测试文件
python -m pytest tests/test_device.py -v

# 运行全部测试
python -m pytest -v

# 生成 HTML 报告（输出到 reports/report.html）
python -m pytest --html=reports/report.html --self-contained-html
```

说明：测试通过 HTTP 调用后端，因此**必须先启动后端**；测试还会直连数据库做断言，
因此后端与测试必须连接**同一个数据库**。

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
- `POST /devices` — 创建设备（owner 由登录用户决定）
- `DELETE /devices/{device_id}` — 删除设备（保留历史操作日志）
- `PUT /devices/{device_id}/status` — 修改状态，`status` 取值 `online` / `offline` / `error`
- `PUT /devices/{device_id}/battery` — 修改电量，`battery` 取值 0-100 的整数
- `GET /operation-logs` — 操作日志（admin 全部，user 仅自己）

### 日志 / 管理员

- `GET /login-logs` — 登录日志（admin 全部，user 仅自己）
- `GET /admin/devices` — 管理员查看全部设备（仅 admin）
- `GET /admin/statistics` — 管理员查看统计（用户数/设备数/在线数/平均电量）

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
