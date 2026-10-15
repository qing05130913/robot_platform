-- ============================================================
-- operation_logs 迁移脚本（A2：删除设备保留历史操作日志）
--
-- 影响范围：仅 operation_logs 表，不删除任何现有数据。
-- 变更内容：
--   1. device_id 改为可空：设备删除后将其置 NULL，而非删除日志；
--   2. 新增 device_name 列：操作日志写入时保存设备名称快照，
--      保证设备删除后日志仍可读（能看出是哪个设备）。
--
-- 执行方式（在项目根目录）：
--   mysql -u root -p robot_platform < sql/migrate_operation_logs.sql
-- ============================================================

ALTER TABLE operation_logs
  MODIFY COLUMN device_id INT NULL COMMENT '关联设备ID（设备删除后置空）',
  ADD COLUMN device_name VARCHAR(100) NULL COMMENT '设备名称快照' AFTER device_id;
