-- Migration: Add session_id to ai_dialogue for multi-session support
-- Run this on existing learning_system database

USE learning_system;

-- 1. Make plan_id nullable (profile dialogues don't have a plan yet)
ALTER TABLE `ai_dialogue`
  MODIFY COLUMN `plan_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '学习计划ID(可为空)';

-- 2. Add session_id column with default for existing records
ALTER TABLE `ai_dialogue`
  ADD COLUMN `session_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '会话ID(UUID)' AFTER `user_id`;

-- 3. Backfill existing records: generate session_id from (user_id, plan_id, intent_type)
-- Use id range to satisfy safe update mode
UPDATE `ai_dialogue` SET `session_id` = CONCAT('legacy-', COALESCE(plan_id, 0), '-', COALESCE(intent_type, 'unknown'))
WHERE `id` > 0;

-- 4. Add index
ALTER TABLE `ai_dialogue`
  ADD INDEX `idx_session_id` (`session_id`);
