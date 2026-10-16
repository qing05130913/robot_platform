-- ============================================================
-- 测试种子数据脚本
-- 请先执行 init.sql 建表，再以目标库执行本脚本，例如：
--   mysql -u root -p robot_platform_test < sql/test_data.sql
-- 注意：本脚本在空表上执行，避免重复执行造成数据重复。
-- ============================================================

-- ------------------------------------------------------------
-- 测试用户
-- 说明：当前阶段尚未实现登录与密码加密，密码暂以明文存储，
--       后续认证阶段将替换为哈希后的密码。
-- ------------------------------------------------------------
INSERT INTO users (username, password, role, status) VALUES
  ('alice', '123456',  'user',  'active'),
  ('bob',   'abcdef',  'user',  'active'),
  ('admin', 'admin123','admin', 'active');

-- ------------------------------------------------------------
-- 测试设备（通过用户名关联所属用户）
-- ------------------------------------------------------------
INSERT INTO devices (name, owner_id, status, battery) VALUES
  ('Robot-A', (SELECT id FROM users WHERE username = 'alice'), 'online', 85),
  ('Robot-B', (SELECT id FROM users WHERE username = 'alice'), 'offline', 60),
  ('Robot-C', (SELECT id FROM users WHERE username = 'bob'), 'online', 92);
