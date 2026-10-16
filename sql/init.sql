-- ============================================================
-- 数据库表结构初始化脚本
--
-- 只负责建表，不创建/选择数据库；目标库由执行命令指定，例如：
--   mysql -u root -p robot_platform_test < sql/init.sql
-- 表结构与后端代码实际使用保持一致：
--   - 所有主键与外键统一使用 INT（与 users.id / devices.id 一致）；
--   - users.role / users.status 使用 VARCHAR（而非 ENUM）；
--   - operation_logs.device_id 可空、含 device_name 快照（设备删除保留历史日志）。
-- ============================================================

-- ------------------------------------------------------------
-- 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id       INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  username VARCHAR(50)  NOT NULL                COMMENT '用户名',
  password VARCHAR(100) NOT NULL                COMMENT '密码',
  role     VARCHAR(20)  NOT NULL DEFAULT 'user' COMMENT '角色：user/admin',
  status   VARCHAR(20)  NOT NULL DEFAULT 'active' COMMENT '状态：active/disabled',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户表';

-- ------------------------------------------------------------
-- 设备表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
  id         INT NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  name       VARCHAR(100) NOT NULL                COMMENT '设备名称',
  owner_id   INT NOT NULL                         COMMENT '所属用户ID',
  status     ENUM('online', 'offline', 'error') NOT NULL DEFAULT 'offline' COMMENT '设备状态',
  battery    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '电量 0-100',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_name (name),
  KEY idx_owner_id (owner_id),
  CONSTRAINT fk_devices_owner FOREIGN KEY (owner_id) REFERENCES users (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '设备表';

-- ------------------------------------------------------------
-- 操作日志表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operation_logs (
  id          INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  user_id     INT NOT NULL COMMENT '操作用户ID',
  device_id   INT NULL COMMENT '关联设备ID（设备删除后置空）',
  device_name VARCHAR(100) NULL COMMENT '设备名称快照（设备删除后仍可读）',
  action      VARCHAR(100) NOT NULL COMMENT '操作类型',
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_device_id (device_id),
  KEY idx_created_at (created_at),
  CONSTRAINT fk_operation_logs_user FOREIGN KEY (user_id) REFERENCES users (id),
  CONSTRAINT fk_operation_logs_device FOREIGN KEY (device_id) REFERENCES devices (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '操作日志表';

-- ------------------------------------------------------------
-- 登录日志表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_logs (
  id         INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  user_id    INT NULL COMMENT '登录用户ID（用户不存在时为 NULL）',
  username   VARCHAR(50) NULL COMMENT '用户名快照',
  result     VARCHAR(20) NOT NULL COMMENT '登录结果：success/failed',
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  CONSTRAINT fk_login_logs_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '登录日志表';
