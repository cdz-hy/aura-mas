CREATE DATABASE IF NOT EXISTS learning_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE learning_system;

CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `login_name` VARCHAR(100) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `nickname` VARCHAR(100) DEFAULT NULL,
    `email` VARCHAR(255) DEFAULT NULL,
    `avatar_url` VARCHAR(500) DEFAULT NULL,
    `role` VARCHAR(30) NOT NULL DEFAULT 'student',
    `status` TINYINT NOT NULL DEFAULT 1,
    `last_login_time` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_login_name` (`login_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

CREATE TABLE IF NOT EXISTS `learning_plan` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '计划ID',
    `title` VARCHAR(255) NOT NULL COMMENT '标题',
    `learning_goal` JSON DEFAULT NULL COMMENT '学习目标',
    `plan_config` JSON DEFAULT NULL COMMENT '计划补充说明',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '关联用户ID',
    `status` TINYINT NOT NULL DEFAULT 0 COMMENT '状态: 0-待规划,1-生成中,2-用户确认中,3-学习中,4-已完成',
    `progress` FLOAT DEFAULT 0.0 COMMENT '整体进度 0-100',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT NOT NULL DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学习计划表';

CREATE TABLE IF NOT EXISTS `learning_resource` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `plan_id` BIGINT UNSIGNED NOT NULL,
    `parent_id` BIGINT UNSIGNED DEFAULT NULL,
    `module_order` INT NOT NULL DEFAULT 0,
    `module_type` VARCHAR(50) NOT NULL,
    `module_data` JSON NOT NULL,
    `status` TINYINT NOT NULL DEFAULT 0,
    `storage_path` VARCHAR(500) DEFAULT NULL,
    `generated_by_agent` VARCHAR(100) DEFAULT NULL,
    `version` INT NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_plan_id` (`plan_id`),
    KEY `idx_parent_id` (`parent_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学习资源表';

CREATE TABLE IF NOT EXISTS `ai_dialogue` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '用户ID',
    `session_id` VARCHAR(36) NOT NULL COMMENT '会话ID(UUID)',
    `plan_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '学习计划ID(可为空)',
    `resource_id` BIGINT UNSIGNED DEFAULT NULL,
    `conversation_text` TEXT NOT NULL,
    `conversation_context` TEXT DEFAULT NULL,
    `dialogue_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `dialogue_type` ENUM('AI', 'USER') NOT NULL,
    `intent_type` VARCHAR(50) DEFAULT NULL,
    `is_deleted` TINYINT NOT NULL DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_plan_id` (`plan_id`),
    KEY `idx_session_id` (`session_id`),
    KEY `idx_resource_id` (`resource_id`),
    KEY `idx_dialogue_time` (`dialogue_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交互式AI对话表';

CREATE TABLE IF NOT EXISTS `quiz_record` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `resource_id` BIGINT UNSIGNED NOT NULL COMMENT '学习资源ID（必须对应题目模块）',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `plan_id` BIGINT UNSIGNED NOT NULL COMMENT '学习计划ID',
    `question_type` VARCHAR(30) DEFAULT NULL COMMENT '题型: single_choice,multiple_choice,true_false,fill_blank,short_answer',
    `difficulty` TINYINT DEFAULT NULL COMMENT '难度 1-5',
    `question_text` TEXT DEFAULT NULL COMMENT '题目内容',
    `correct_answer` TEXT COMMENT '正确答案',
    `user_answer` TEXT COMMENT '用户作答',
    `score` DOUBLE DEFAULT NULL COMMENT 'LLM 评分 0-1',
    `is_correct` TINYINT DEFAULT NULL COMMENT '0错误 1正确',
    `feedback` TEXT DEFAULT NULL COMMENT 'LLM 详细反馈',
    `answer_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作答时间',
    `is_deleted` TINYINT DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_resource_id` (`resource_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_plan_id` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='答题表';

CREATE TABLE IF NOT EXISTS `user_profile` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `version` INT NOT NULL,
    `is_current` TINYINT NOT NULL DEFAULT 0,
    `age` VARCHAR(10) DEFAULT NULL,
    `gender` VARCHAR(10) DEFAULT NULL,
    `domain` VARCHAR(100) DEFAULT NULL,
    `learning_behavior` JSON DEFAULT NULL,
    `update_reason` VARCHAR(255) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_current` (`user_id`, `is_current`),
    KEY `idx_user_version` (`user_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户画像表';

CREATE TABLE IF NOT EXISTS `note` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `note_name` VARCHAR(255) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `tags` JSON DEFAULT NULL COMMENT '标签数组',
    `is_pinned` TINYINT DEFAULT 0 COMMENT '是否置顶',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='笔记表';

CREATE TABLE IF NOT EXISTS `note_resource_rel` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `note_id` BIGINT UNSIGNED NOT NULL,
    `resource_id` BIGINT UNSIGNED NOT NULL,
    `selected_text` TEXT DEFAULT NULL COMMENT '选中的原文',
    `position_info` VARCHAR(255) DEFAULT NULL COMMENT '选区位置信息',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_note_resource` (`note_id`, `resource_id`),
    KEY `idx_resource_id` (`resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='笔记学习资源关联表';

-- 如果表已存在，执行以下 ALTER 语句：
-- ALTER TABLE note_resource_rel ADD COLUMN selected_text TEXT DEFAULT NULL COMMENT '选中的原文';
-- ALTER TABLE note_resource_rel ADD COLUMN position_info VARCHAR(255) DEFAULT NULL COMMENT '选区位置信息';
-- ALTER TABLE note_resource_rel ADD COLUMN plan_id BIGINT UNSIGNED DEFAULT NULL COMMENT '学习计划ID';
-- ALTER TABLE note_resource_rel ADD COLUMN module_name VARCHAR(255) DEFAULT NULL COMMENT '模块名称';
-- ALTER TABLE note_resource_rel ADD COLUMN resource_title VARCHAR(255) DEFAULT NULL COMMENT '资源标题';

-- 笔记标签和置顶功能：
-- ALTER TABLE note ADD COLUMN tags JSON DEFAULT NULL COMMENT '标签数组' AFTER content;
-- ALTER TABLE note ADD COLUMN is_pinned TINYINT DEFAULT 0 COMMENT '是否置顶' AFTER tags;

CREATE TABLE IF NOT EXISTS `flashcard` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `note_id` BIGINT UNSIGNED NOT NULL COMMENT '所属笔记ID',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `question` TEXT NOT NULL COMMENT '问题（正面）',
    `answer` TEXT NOT NULL COMMENT '答案（背面）',
    `difficulty` TINYINT DEFAULT 1 COMMENT '初始难度 1-简单 2-中等 3-困难',
    `ease_factor` DOUBLE DEFAULT 2.5 COMMENT 'SM-2 简易因子',
    `review_interval` INT DEFAULT 0 COMMENT '当前复习间隔（天）',
    `review_count` INT DEFAULT 0 COMMENT '已复习次数',
    `next_review_at` DATETIME DEFAULT NULL COMMENT '下次复习时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_note_id` (`note_id`),
    KEY `idx_user_next_review` (`user_id`, `next_review_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='闪卡表';

CREATE TABLE IF NOT EXISTS `knowledge_base` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `doc_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_size` BIGINT DEFAULT NULL,
    `chunk_count` INT DEFAULT NULL,
    `parse_status` TINYINT NOT NULL DEFAULT 0,
    `collection_name` VARCHAR(255) DEFAULT NULL,
    `mineru_task_id` VARCHAR(100) DEFAULT NULL,
    `upload_user_id` BIGINT UNSIGNED NOT NULL,
    `upload_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_upload_user` (`upload_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库管理表';

CREATE TABLE IF NOT EXISTS `ai_kb_generation` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `api_call_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `result_path` VARCHAR(500) DEFAULT NULL,
    `operator_id` BIGINT UNSIGNED NOT NULL,
    `call_params` JSON DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_operator` (`operator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI知识库补充生成表';

CREATE TABLE IF NOT EXISTS `system_log` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED DEFAULT NULL,
    `operation_type` VARCHAR(50) NOT NULL,
    `resource_id` VARCHAR(255) DEFAULT NULL,
    `user_ip` VARCHAR(45) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_operation` (`operation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统操作日志表';

CREATE TABLE IF NOT EXISTS `ai_token_usage` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `task_id` BIGINT UNSIGNED DEFAULT NULL,
    `scene` VARCHAR(100) NOT NULL,
    `model_name` VARCHAR(100) NOT NULL,
    `input_tokens` INT NOT NULL DEFAULT 0,
    `output_tokens` INT NOT NULL DEFAULT 0,
    `total_tokens` INT GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI Token消耗表';

CREATE TABLE IF NOT EXISTS `learning_duration` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `plan_id` BIGINT UNSIGNED NOT NULL,
    `resource_id` BIGINT UNSIGNED DEFAULT NULL,
    `start_time` DATETIME NOT NULL,
    `end_time` DATETIME DEFAULT NULL,
    `duration_seconds` INT DEFAULT NULL,
    `terminal_type` VARCHAR(30) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_plan` (`user_id`, `plan_id`),
    KEY `idx_resource` (`resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户学习时长记录表';

CREATE TABLE IF NOT EXISTS `ai_feedback` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `target_type` VARCHAR(50) NOT NULL,
    `target_id` BIGINT UNSIGNED NOT NULL,
    `rating` TINYINT NOT NULL,
    `suggestion` TEXT DEFAULT NULL,
    `feedback_type` ENUM('评分','建议','错误报告') DEFAULT '评分',
    `admin_viewed` TINYINT NOT NULL DEFAULT 0,
    `resolved_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_target` (`target_type`, `target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI内容反馈表';

CREATE TABLE IF NOT EXISTS `user_learning_progress` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `plan_id` BIGINT UNSIGNED NOT NULL,
    `resource_id` BIGINT UNSIGNED NOT NULL,
    `status` TINYINT NOT NULL DEFAULT 0,
    `start_time` DATETIME DEFAULT NULL,
    `complete_time` DATETIME DEFAULT NULL,
    `last_access_time` DATETIME DEFAULT NULL,
    `duration_seconds` INT DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_plan_resource` (`user_id`, `plan_id`, `resource_id`),
    KEY `idx_plan_status` (`plan_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户学习进度表';

CREATE TABLE IF NOT EXISTS `resource_generation_task` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `plan_id` BIGINT UNSIGNED NOT NULL,
    `resource_id` BIGINT UNSIGNED NOT NULL,
    `task_status` TINYINT NOT NULL DEFAULT 0,
    `agent_chain` JSON DEFAULT NULL,
    `retry_count` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `finished_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_plan_resource` (`plan_id`, `resource_id`),
    KEY `idx_status` (`task_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资源生成任务表';

CREATE TABLE IF NOT EXISTS `menu` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code` VARCHAR(100) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `path` VARCHAR(255) DEFAULT NULL,
    `icon` VARCHAR(100) DEFAULT NULL,
    `parent_id` BIGINT UNSIGNED DEFAULT NULL,
    `type` VARCHAR(20) NOT NULL DEFAULT 'menu',
    `sort_order` INT NOT NULL DEFAULT 0,
    `is_deleted` TINYINT DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_code` (`code`),
    KEY `idx_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜单权限表';

CREATE TABLE IF NOT EXISTS `role_menu` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `role` VARCHAR(30) NOT NULL,
    `menu_id` BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_role_menu` (`role`, `menu_id`),
    KEY `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色菜单关联表';

CREATE TABLE IF NOT EXISTS `daily_study_time` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `study_date` DATE NOT NULL,
    `duration_seconds` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_date` (`user_id`, `study_date`),
    KEY `idx_user_date` (`user_id`, `study_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日学习时长表';
