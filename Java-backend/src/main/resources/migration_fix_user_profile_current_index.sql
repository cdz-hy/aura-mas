-- Migration: Allow multiple historical user_profile versions
-- Run this on existing learning_system database.
--
-- The previous UNIQUE(user_id, is_current) index allowed only one inactive
-- historical profile row per user because all old versions use is_current=0.
-- UserService already marks only the latest row as is_current=1.

USE learning_system;

ALTER TABLE `user_profile`
  DROP INDEX `uk_user_current`;

ALTER TABLE `user_profile`
  ADD INDEX `idx_user_current` (`user_id`, `is_current`);
