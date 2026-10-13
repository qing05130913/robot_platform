# 项目：机器人设备管理平台接口自动化测试

## 项目目的
这是测试开发学习项目。
FastAPI 后端只是被测系统 SUT。
主要学习方向：Python + requests + pytest + MySQL + PyMySQL + 自动化测试。

## 技术栈
后端：FastAPI + PyMySQL + MySQL
测试：Python + requests + pytest

## 当前后端阶段
已完成：
1. 项目基础
2. MySQL 数据库
3. 登录接口 POST /login

当前正在做：
POST /login 的 pytest + requests 自动化测试。

## 数据库
数据库：robot_platform

主要表：
users
devices
operation_logs
login_logs

## 登录账号
alice / 123456
bob / abcdef
admin / admin123

## POST /login
正常：
HTTP 200
code = 0

用户不存在：
HTTP 401
code = 10001

密码错误：
HTTP 401
code = 10002

用户禁用：
HTTP 403
code = 10003

参数校验失败：
HTTP 422

## 后续计划
完成登录自动化测试后：
第三阶段：用户接口
第四阶段：设备接口
第五阶段：日志
第六阶段：管理员
后续加入数据库校验、权限测试、Mock、报告等。