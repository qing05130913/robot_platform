-- ============================================================
-- robot_platform 数据库初始化脚本
-- 负责创建数据库和核心表
-- ============================================================

CREATE DATABASE IF NOT EXISTS robot_platform
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE robot_platform;

-- ------------------------------------------------------------
-- 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  username   VARCHAR(50)     NOT NULL                COMMENT '用户名',
  password   VARCHAR(255)    NOT NULL                COMMENT '密码',
  role       ENUM('user', 'admin') NOT NULL DEFAULT 'user' COMMENT '角色',
  status     ENUM('active', 'disabled') NOT NULL DEFAULT 'active' COMMENT '状态',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户表';

-- ------------------------------------------------------------
-- 设备表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  name       VARCHAR(100) NOT NULL                COMMENT '设备名称',
  owner_id   BIGINT UNSIGNED NOT NULL             COMMENT '所属用户ID',
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
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  user_id    BIGINT UNSIGNED NOT NULL COMMENT '操作用户ID',
  device_id  BIGINT UNSIGNED NOT NULL COMMENT '关联设备ID',
  action     VARCHAR(100) NOT NULL COMMENT '操作类型',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
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
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  user_id    BIGINT UNSIGNED NULL COMMENT '登录用户ID',
  login_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
  ip         VARCHAR(45) NULL COMMENT '登录IP',
  result     ENUM('success', 'failed') NOT NULL DEFAULT 'success' COMMENT '登录结果',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_login_time (login_time),
  CONSTRAINT fk_login_logs_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '登录日志表';
