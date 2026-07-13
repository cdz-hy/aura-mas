-- Migration: Add note capture metadata for sidebar workbench
-- Run this on existing learning_system database

USE learning_system;

ALTER TABLE `note`
  ADD COLUMN `note_type` VARCHAR(32) DEFAULT NULL COMMENT '摘录/速记/提问: excerpt|quick|question' AFTER `is_pinned`,
  ADD COLUMN `organize_status` VARCHAR(32) DEFAULT NULL COMMENT '整理状态: pending|organizing|organized|error' AFTER `note_type`,
  ADD COLUMN `source_type` VARCHAR(64) DEFAULT NULL COMMENT '来源类型: resource|plan|knowledge_tree|tutor' AFTER `organize_status`,
  ADD COLUMN `source_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '来源实体ID' AFTER `source_type`,
  ADD COLUMN `source_title` VARCHAR(255) DEFAULT NULL COMMENT '来源标题' AFTER `source_id`,
  ADD COLUMN `source_route` VARCHAR(512) DEFAULT NULL COMMENT '来源前端路由' AFTER `source_title`,
  ADD COLUMN `excerpt` TEXT DEFAULT NULL COMMENT '摘录原文（可为空）' AFTER `source_route`,
  ADD INDEX `idx_organize_status` (`organize_status`);
