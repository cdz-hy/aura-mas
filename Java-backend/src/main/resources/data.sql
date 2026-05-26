USE learning_system;

-- 清理旧的 admin-section 数据（如果存在）
DELETE FROM role_menu WHERE menu_id IN (SELECT id FROM menu WHERE code = 'admin-section');
DELETE FROM menu WHERE code = 'admin-section';

-- ============================================================
-- Seed data: menus
-- ============================================================
INSERT IGNORE INTO menu (code, name, path, icon, type, sort_order) VALUES
('dashboard',      '学习概览',  '/dashboard',    'dashboard', 'menu', 1),
('plan-list',      '学习计划',  '/plan/create',  'plan',      'menu', 2),
('note-list',      '我的笔记',  '/notes',        'notes',     'menu', 3),
('profile',        '我的画像',  '/profile',      'profile',   'menu', 4),
('admin-dashboard','管理概览',  '/admin',        'admin',     'menu', 101),
('kb-management',  '知识库管理','/admin/kb',     'book',      'menu', 102),
('user-management','用户管理',  '/admin/users',  'users',     'menu', 103);

-- 确保管理菜单没有父级（避免残留的 parent_id 导致路由异常）
UPDATE menu SET parent_id = NULL WHERE code IN ('admin-dashboard', 'kb-management', 'user-management');

-- ============================================================
-- Seed data: role_menu 角色菜单分配
-- ============================================================
INSERT IGNORE INTO role_menu (role, menu_id)
SELECT 'student', id FROM `menu` WHERE code IN ('dashboard', 'plan-list', 'note-list', 'profile');

INSERT IGNORE INTO role_menu (role, menu_id)
SELECT 'admin', id FROM `menu`
WHERE code IN ('admin-dashboard', 'kb-management', 'user-management');
