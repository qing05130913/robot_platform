# Robot Platform 接口自动化测试项目

机器人设备管理平台：FastAPI 后端作为被测系统（SUT），测试侧使用 Python + requests + pytest + PyMySQL 对接口进行自动化验证。项目重点不是前端页面或机器人控制，而是接口测试设计、权限矩阵、数据库一致性校验、契约校验、测试数据隔离和 CI 自动化执行。

当前测试规模：**121 条用例 / 6 个测试模块 / 14 个业务接口**（另有 `/`、`/test-db` 两个辅助接口）。测试在独立测试库 `robot_platform_test` 上运行。

## 技术栈

| 端 | 技术 |
|---|---|
| 后端（SUT） | Python 3.10+（CI 使用 3.12）、FastAPI、Uvicorn、Pydantic、PyMySQL、MySQL（CI 使用 8.0）、python-dotenv |
| 测试 | pytest、requests、PyMySQL、pytest-html |
| CI | GitHub Actions（Ubuntu、MySQL 8.0 service） |

后端使用 PyMySQL 原生 SQL，没有引入 ORM/SQLAlchemy；测试侧通过 HTTP 调用后端，并用 PyMySQL 做数据库断言。

## 项目结构

```text
backend-demo/
├── .github/workflows/ci.yml       # GitHub Actions：启动 MySQL + SUT，执行 pytest
├── backend/                       # 被测系统（SUT）
│   ├── main.py                    # FastAPI 入口、路由注册、统一异常响应
│   ├── database.py                # 数据库连接、测试库安全校验
│   ├── routers/                   # 路由层
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── devices.py
│   │   ├── login_logs.py
│   │   └── admin.py
│   ├── schemas/                   # Pydantic 请求/响应模型
│   ├── services/                  # 业务逻辑与 SQL
│   └── utils/auth.py              # Token 解析、当前用户依赖
├── common/                        # 测试公共能力
│   ├── api_client.py              # requests 封装：Token、超时、日志、脱敏
│   ├── assertions.py              # 统一断言与契约校验
│   └── logger.py                  # 日志配置（文件轮转）
├── tests/                         # 测试用例
│   ├── conftest.py                # api_client / db / users / devices fixture
│   ├── test_login.py
│   ├── test_user.py
│   ├── test_device.py
│   ├── test_log.py
│   ├── test_admin.py
│   └── test_contract.py           # 契约守卫自身的负向测试
├── sql/
│   ├── init.sql                   # 建表（目标库由命令指定）
│   ├── test_data.sql              # 种子用户与设备
│   └── migrate_operation_logs.sql # 旧库升级（保留历史日志）
├── config.py                      # 测试侧 BASE_URL / TIMEOUT
├── pytest.ini
├── requirements.txt
├── start_test_backend.ps1         # 启动连接测试库的后端
├── run_tests.ps1                  # 设置测试库环境后执行 pytest
├── .env.example
└── README.md
```

`logs/`、`reports/` 为运行产物，已在 `.gitignore` 中忽略。

## 测试设计与工程实践

### 1. APIClient 封装

`common/api_client.py` 基于 `requests` 封装 GET/POST/PUT/DELETE：

- 自动把 `token` 转换为 `Authorization: Bearer <token>`；
- 统一设置超时（默认 5 秒，来自 `TIMEOUT`）；
- 记录请求/响应日志：方法、URL、请求体；响应体超过 1000 字符截断；
- 请求体中的 `password` 字段自动打码为 `***`；
- 非 2xx 响应以 WARNING 记录，便于定位失败接口。

### 2. pytest fixture

`tests/conftest.py` 管理测试共享资源：

- `api_client`：session 级，无状态复用；
- `_require_test_database`：session 级 autouse，执行 `SELECT DATABASE()`，实际库不是 `robot_platform_test` 时直接失败；
- `db`：function 级 PyMySQL 连接，显式 `autocommit(True)`，用后关闭；
- `users` / `devices`：按 `username` / 设备名动态解析主键，测试不硬编码自增 ID。

`autocommit` 是为了避免 InnoDB REPEATABLE READ 在“先读、API 写入、后回读”时读到旧快照，导致数据库断言失真。

### 3. 权限矩阵

- `tests/test_device.py` 用 `USERNAMES × DEVICE_NAMES` 参数化覆盖 alice/bob/admin × Robot-A/B/C，测试侧用 `expected_permission_status` 独立计算预期权限；
- `tests/test_user.py` 覆盖普通用户/管理员对用户资源的 3×3 访问矩阵；
- 统一验证 401（未认证）、403（无权限）、404（admin 查询不存在资源）；
- 普通用户访问不存在的设备统一返回 403，避免泄露资源是否存在。

### 4. 正常、异常与边界场景

- 登录：成功、密码错误、用户不存在、空参数、禁用用户；
- 设备：列表/详情/创建/删除、状态与电量更新、名称重复、非法状态、电量 0/1/99/100 与 -1/101/50.5 等边界；
- 用户与日志：当前用户、用户列表权限、登录日志过滤、失败登录的用户名快照；
- 管理员：设备列表、统计接口权限。

### 5. 数据库一致性校验（DB Oracle）

测试不仅看 HTTP 响应，还直接查数据库：

- 设备状态/电量更新：HTTP 成功 + GET 回读 + DB 直查 + 操作日志恰好新增一条；
- 删除设备：设备删除后 `operation_logs.device_id` 置空，`device_name` 快照保留；
- 管理员统计：请求前用独立 SQL 计算用户数、设备数、在线/离线数、平均电量，再与接口结果比较；
- 操作日志权限：测试自己造带唯一标记的日志，验证普通用户只看到自己的、admin 看到全部。

### 6. Pydantic 响应契约

`common/assertions.py` 的 `assert_contract` 复用 `backend/schemas` 的响应模型，校验字段是否齐全、类型是否正确。接口模型是唯一事实来源，避免测试侧另写一份 schema 产生漂移。

`tests/test_contract.py` 用 `FakeResponse` 做负向证明：字段缺失或类型变化时，契约断言必须报错。契约校验只负责结构，具体业务取值由业务断言和 DB Oracle 负责。

### 7. 多层断言与公共断言

`common/assertions.py` 统一封装：

- `assert_success`：HTTP 200 + 业务 `code=0`；
- `assert_biz_error`：HTTP 状态码 + 业务错误码；
- `assert_validation_error`：422 参数校验；
- `assert_contract`：Pydantic 响应结构。

一个成功用例通常同时验证：HTTP 状态码、业务响应 `code`、`data` 内容、GET 回读、数据库最终状态、操作日志。

### 8. 日志与敏感信息

- `common/logger.py` 配置控制台 + `RotatingFileHandler`（单文件 1 MB，保留 3 个备份），日志写入 `logs/test.log`；
- `APIClient` 对请求体中的 `password` 打码，响应体过长时截断，避免日志泄漏敏感信息或无限膨胀。

### 9. 测试数据库隔离与测试数据自足

- 开发库 `robot_platform`：日常开发；
- 测试库 `robot_platform_test`：pytest 与测试后端都必须连接它；
- 两层护栏：
  1. pytest 侧 `tests/conftest.py` 执行 `SELECT DATABASE()`，连错库直接失败；
  2. 后端 `TEST_MODE=1` 时，`backend/main.py` 启动校验实际库必须是 `robot_platform_test`，否则拒绝启动；
- 测试数据：UUID 设备名、`try/finally` / fixture 清理、按业务键动态解析主键；
- `operation_logs` / `login_logs` 为 append-only，测试不清理全表，只清理自己创建的数据。

## 接口功能与权限

### 认证方式

登录成功返回固定格式 Token：`token_<username>`。后续请求携带：

```http
Authorization: Bearer token_alice
```

该 Token 格式是测试项目的简化实现，仅用于本地/测试环境，不代表生产级认证方案。

### 接口清单

**认证 / 用户**

- `POST /login` — 登录，返回 token、user_id、username、role；
- `GET /user` — 当前登录用户信息；
- `GET /users` — 用户列表（仅 admin）；
- `GET /users/{user_id}` — 指定用户（admin 任意，普通用户仅自己）。

**设备**

- `GET /devices` — 设备列表（admin 全部，普通用户仅自己）；
- `GET /devices/{device_id}` — 设备详情（admin 任意，普通用户仅自己）；
- `POST /devices` — 创建设备（owner 由当前登录用户决定，名称唯一）；
- `DELETE /devices/{device_id}` — 删除设备（保留历史操作日志）；
- `PUT /devices/{device_id}/status` — 修改状态：`online` / `offline` / `error`，写操作日志；
- `PUT /devices/{device_id}/battery` — 修改电量：0–100 整数，写操作日志；
- `GET /operation-logs` — 操作日志（admin 全部，普通用户仅自己）。

**日志 / 管理员**

- `GET /login-logs` — 登录日志（admin 全部，普通用户仅自己）；
- `GET /admin/devices` — 管理员查看全部设备（仅 admin）；
- `GET /admin/statistics` — 管理员统计：用户数、设备数、在线/离线数、平均电量（仅 admin）。

**辅助接口**

- `GET /` — 服务健康检查；
- `GET /test-db` — 数据库连通性检查，返回实际库名和 MySQL 版本。

### 权限规则

- admin 可访问全部设备、用户、日志和管理员接口；
- 普通用户只能访问自己的设备、自己的用户信息、自己的操作日志和登录日志；
- 普通用户访问不存在的设备返回 403，admin 返回 404，避免泄露资源存在性；
- 创建设备的 `owner_id` 由当前登录用户自动确定，不接受客户端传入；
- 删除设备、修改设备状态/电量：admin 任意，普通用户仅自己的设备；
- 用户列表、管理员设备列表、统计接口仅 admin。

### 业务错误码

响应统一为 `{code, message, data}`；参数校验失败返回 422，`data` 为校验错误列表。

| code | 含义 | HTTP |
|---|---|---|
| 0 | 成功 | 200 |
| 10001 | 用户不存在（登录） | 401 |
| 10002 | 密码错误 | 401 |
| 10003 | 用户被禁用 | 403 |
| 400 | 设备名称已存在 | 400 |
| 10401 | 未提供 Token / Token 无效 | 401 |
| 10403 | 无权限访问 | 403 |
| 10404 | 用户/设备不存在 | 404 |
| 422 | 参数校验失败 | 422 |

## 数据库配置与本地运行

### 环境变量

连接配置由 `backend/database.py` 从环境变量读取；测试侧 `config.py` 读取 `BASE_URL` / `TIMEOUT`。首次使用可复制 `.env.example` 为 `.env` 后修改；`.env` 已被 gitignore。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DB_HOST` | `127.0.0.1` | 数据库地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `DB_USER` | `root` | 数据库用户名 |
| `DB_PASSWORD` | （空） | 数据库密码 |
| `DB_NAME` | `robot_platform` | 数据库名 |
| `BASE_URL` | `.env` 配置 | 测试侧后端地址，如 `http://127.0.0.1:8000` |
| `TIMEOUT` | `5` | 测试请求超时（秒） |

### 初始化数据库

`init.sql` 只负责建表，不创建/选择数据库；目标库名由命令指定。

PowerShell 中 `<` 不是可用的输入重定向符，下面用 `cmd /c` 包一层；如果你在 cmd.exe 中执行，可以去掉 `cmd /c`。

**开发库 `robot_platform`：**

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS robot_platform DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"

cmd /c "mysql --default-character-set=utf8mb4 -u root -p robot_platform < sql\init.sql"
cmd /c "mysql --default-character-set=utf8mb4 -u root -p robot_platform < sql\test_data.sql"
```

**测试库 `robot_platform_test`：**

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS robot_platform_test DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"

cmd /c "mysql --default-character-set=utf8mb4 -u root -p robot_platform_test < sql\init.sql"
cmd /c "mysql --default-character-set=utf8mb4 -u root -p robot_platform_test < sql\test_data.sql"
```

种子数据：`alice/123456`、`bob/abcdef`、`admin/admin123`，设备 `Robot-A`、`Robot-B`、`Robot-C`。仅用于本地/测试环境。

旧库升级：若旧库的 `operation_logs` 还没有 `device_name` 列，或 `device_id` 仍不可空，执行：

```powershell
cmd /c "mysql --default-character-set=utf8mb4 -u root -p robot_platform < sql\migrate_operation_logs.sql"
```

新建的 `robot_platform_test` 不需要该迁移。

### 启动后端

**日常开发后端（连接 `robot_platform`）：**

```powershell
cd backend
uvicorn main:app --reload
```

**测试专用后端（连接 `robot_platform_test`）：**

```powershell
.\start_test_backend.ps1
```

脚本会设置 `DB_NAME=robot_platform_test`、`TEST_MODE=1`，然后进入 `backend` 启动 uvicorn。`TEST_MODE=1` 下如果实际连的不是测试库，后端会拒绝启动。

也可以手动：

```powershell
cd backend
$env:DB_NAME = "robot_platform_test"
$env:TEST_MODE = "1"
uvicorn main:app --reload
```

### 运行测试

先启动“测试专用后端”，再在另一个终端、项目根目录执行。

```powershell
# 全量
.\run_tests.ps1

# 单个文件
.\run_tests.ps1 tests/test_device.py -v

# 单个用例
.\run_tests.ps1 tests/test_login.py::test_login_success -v

# 生成 HTML 报告
New-Item -ItemType Directory -Force .\reports | Out-Null
.\run_tests.ps1 --html=reports/report.html --self-contained-html
```

`run_tests.ps1` 会设置 `DB_NAME=robot_platform_test` 后执行 `python -m pytest`。

也可以手动执行：

```powershell
$env:DB_NAME = "robot_platform_test"
python -m pytest -v
```

说明：

- 测试通过 HTTP 调用后端，因此必须先启动测试专用后端；
- pytest 也会直连数据库，`tests/conftest.py` 会校验实际连接的是 `robot_platform_test`，连错直接失败；
- 可用 `GET /test-db` 确认后端连接的库名；
- `reports/`、`logs/` 为本地运行产物，不提交到仓库。

## CI 自动化测试

GitHub Actions 配置在 `.github/workflows/ci.yml`，触发条件：

- push 到 `master`；
- 向 `master` 提交 pull request。

执行环境与流程：

1. `ubuntu-latest` 运行；
2. 启动 MySQL 8.0 service，配置健康检查；
3. 设置 `DB_NAME=robot_platform_test`、`TEST_MODE=1`、`BASE_URL=http://127.0.0.1:8000`；
4. 安装 `requirements.txt` 依赖；
5. 创建测试库，执行 `sql/init.sql` 和 `sql/test_data.sql`；
6. 用 `uvicorn main:app --app-dir backend` 启动 FastAPI；
7. 轮询 `GET /test-db`，确认后端和测试库就绪；
8. 执行全量 `pytest`，生成 `reports/report.html`；
9. 无论测试是否通过，都上传 HTML 报告 artifact（`pytest-html-report`）。

CI 每次使用全新的 MySQL 数据库，因此不需要执行本地旧库迁移脚本。项目实现的是 **CI 自动化接口测试**，不包含自动部署或发布流程。

## 测试规模与验证结果

| 测试模块 | 用例数 | 主要内容 |
|---|---:|---|
| `tests/test_login.py` | 6 | 登录成功/失败、参数校验、禁用用户 |
| `tests/test_user.py` | 17 | 当前用户、用户权限矩阵、用户列表 |
| `tests/test_device.py` | 84 | 设备增删改查、状态/电量、权限矩阵、边界、DB 一致性、日志保留 |
| `tests/test_log.py` | 5 | 登录日志权限过滤、失败登录用户名快照 |
| `tests/test_admin.py` | 6 | 管理员设备列表、统计接口独立 DB Oracle、权限 |
| `tests/test_contract.py` | 3 | 契约守卫的缺失字段/类型错误负向证明 |
| **合计** | **121** | 参数化用例按实际 collected 数统计 |

其他项目数据：

- 业务接口：14 个；辅助接口：2 个（`/`、`/test-db`）；
- 测试模块：6 个；
- 数据库表：4 张（`users`、`devices`、`operation_logs`、`login_logs`）；
- 种子数据：3 个用户、3 台设备。

当前测试代码通过 `pytest --collect-only` 收集到 **121 条用例**。本地在 `robot_platform_test` 上最近一次全量执行结果为 **121 passed**；HTML 报告可通过上述命令生成。

项目未统计测试覆盖率或性能数据，也不宣称这些指标。

## 项目边界

- 这是接口自动化测试学习项目，不是完整的生产系统；
- 不包含前端页面、真实机器人通信、任务调度或自动部署；
- Token 使用固定格式 `token_<username>`，种子密码为明文，仅用于测试环境，不代表生产安全方案；
- 测试串行执行，未做并发压测、覆盖率统计或性能测试；
- `operation_logs` / `login_logs` 为 append-only，测试只清理自己创建的数据。

## 验证

- 服务健康检查：`http://127.0.0.1:8000/`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- 数据库连通性：`http://127.0.0.1:8000/test-db`
- 在 Swagger 中点击 **Authorize**，填入 `token_alice` 等 Token，即可调试受保护接口。
