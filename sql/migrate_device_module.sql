-- ============================================================
-- 设备模块迁移脚本
-- 用于已按上一阶段初始化的数据库：重建 devices 与 operation_logs
-- 表结构并写入设备测试数据。users 与 login_logs 保持不变。
--
-- 说明：users.id 实际类型为 INT，因此所有外键列均使用 INT，
--       以保证与 users.id / devices.id 完全兼容。
-- ============================================================

USE robot_platform;

-- 先删除依赖表（operation_logs 外键引用 devices）
DROP TABLE IF EXISTS operation_logs;
DROP TABLE IF EXISTS devices;

CREATE TABLE devices (
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

CREATE TABLE operation_logs (
  id         INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  user_id    INT NOT NULL COMMENT '操作用户ID',
  device_id  INT NOT NULL COMMENT '关联设备ID',
  action     VARCHAR(100) NOT NULL COMMENT '操作类型',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_device_id (device_id),
  KEY idx_created_at (created_at),
  CONSTRAINT fk_operation_logs_user FOREIGN KEY (user_id) REFERENCES users (id),
  CONSTRAINT fk_operation_logs_device FOREIGN KEY (device_id) REFERENCES devices (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '操作日志表';

-- 设备测试数据
INSERT INTO devices (name, owner_id, status, battery) VALUES
  ('Robot-A', (SELECT id FROM users WHERE username = 'alice'), 'online', 85),
  ('Robot-B', (SELECT id FROM users WHERE username = 'alice'), 'offline', 60),
  ('Robot-C', (SELECT id FROM users WHERE username = 'bob'), 'online', 92);
