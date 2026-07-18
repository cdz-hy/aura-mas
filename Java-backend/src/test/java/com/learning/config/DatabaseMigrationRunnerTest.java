package com.learning.config;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class DatabaseMigrationRunnerTest {

    @Test
    void replacesLegacyUserProfileCurrentUniqueIndex() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "user_profile", "uk_user_current"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "user_profile", "idx_user_current"))
                .thenReturn(0);

        runner.fixUserProfileCurrentIndex();

        var inOrder = inOrder(jdbcTemplate);
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)");
    }

    @Test
    void doesNothingWhenLegacyUserProfileCurrentIndexIsAbsent() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "user_profile", "uk_user_current"))
                .thenReturn(0);

        runner.fixUserProfileCurrentIndex();

        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)"));
    }

    @Test
    void doesNotCreateDuplicateNormalIndexWhenItAlreadyExists() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "user_profile", "uk_user_current"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "user_profile", "idx_user_current"))
                .thenReturn(1);

        runner.fixUserProfileCurrentIndex();

        verify(jdbcTemplate).execute("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`");
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)"));
    }

    @Test
    void addsMissingNoteColumnsForLegacyTables() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        stubNoteColumnMissing(jdbcTemplate, "tags");
        stubNoteColumnMissing(jdbcTemplate, "is_pinned");
        stubNoteColumnMissing(jdbcTemplate, "note_type");
        stubNoteColumnMissing(jdbcTemplate, "organize_status");
        stubNoteColumnMissing(jdbcTemplate, "source_type");
        stubNoteColumnMissing(jdbcTemplate, "source_id");
        stubNoteColumnMissing(jdbcTemplate, "source_title");
        stubNoteColumnMissing(jdbcTemplate, "source_route");
        stubNoteColumnMissing(jdbcTemplate, "excerpt");
        stubNoteColumnMissing(jdbcTemplate, "is_deleted");
        stubNoteColumnMissing(jdbcTemplate, "deleted_at");
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "note", "idx_organize_status"))
                .thenReturn(0);

        runner.ensureNoteColumns();

        var inOrder = inOrder(jdbcTemplate);
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '标签数组' AFTER `content`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `is_pinned` TINYINT DEFAULT 0 COMMENT '是否置顶' AFTER `tags`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `note_type` VARCHAR(32) DEFAULT NULL COMMENT '摘录/速记/提问: excerpt|quick|question' AFTER `is_pinned`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `organize_status` VARCHAR(32) DEFAULT NULL COMMENT '整理状态: pending|organizing|organized|error' AFTER `note_type`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `source_type` VARCHAR(64) DEFAULT NULL COMMENT '来源类型: resource|plan|knowledge_tree|tutor' AFTER `organize_status`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `source_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '来源实体ID' AFTER `source_type`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `source_title` VARCHAR(255) DEFAULT NULL COMMENT '来源标题' AFTER `source_id`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `source_route` VARCHAR(512) DEFAULT NULL COMMENT '来源前端路由' AFTER `source_title`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `excerpt` TEXT DEFAULT NULL COMMENT '摘录原文（可为空）' AFTER `source_route`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD INDEX `idx_organize_status` (`organize_status`)");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `is_deleted` TINYINT DEFAULT 0 AFTER `updated_at`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `deleted_at` DATETIME DEFAULT NULL AFTER `is_deleted`");
    }

    @Test
    void doesNotAddExistingNoteColumns() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        stubNoteColumnPresent(jdbcTemplate, "tags");
        stubNoteColumnPresent(jdbcTemplate, "is_pinned");
        stubNoteColumnPresent(jdbcTemplate, "note_type");
        stubNoteColumnPresent(jdbcTemplate, "organize_status");
        stubNoteColumnPresent(jdbcTemplate, "source_type");
        stubNoteColumnPresent(jdbcTemplate, "source_id");
        stubNoteColumnPresent(jdbcTemplate, "source_title");
        stubNoteColumnPresent(jdbcTemplate, "source_route");
        stubNoteColumnPresent(jdbcTemplate, "excerpt");
        stubNoteColumnPresent(jdbcTemplate, "is_deleted");
        stubNoteColumnPresent(jdbcTemplate, "deleted_at");
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "note", "idx_organize_status"))
                .thenReturn(1);

        runner.ensureNoteColumns();

        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '标签数组' AFTER `content`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `is_pinned` TINYINT DEFAULT 0 COMMENT '是否置顶' AFTER `tags`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `note_type` VARCHAR(32) DEFAULT NULL COMMENT '摘录/速记/提问: excerpt|quick|question' AFTER `is_pinned`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `organize_status` VARCHAR(32) DEFAULT NULL COMMENT '整理状态: pending|organizing|organized|error' AFTER `note_type`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `source_type` VARCHAR(64) DEFAULT NULL COMMENT '来源类型: resource|plan|knowledge_tree|tutor' AFTER `organize_status`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `source_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '来源实体ID' AFTER `source_type`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `source_title` VARCHAR(255) DEFAULT NULL COMMENT '来源标题' AFTER `source_id`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `source_route` VARCHAR(512) DEFAULT NULL COMMENT '来源前端路由' AFTER `source_title`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `excerpt` TEXT DEFAULT NULL COMMENT '摘录原文（可为空）' AFTER `source_route`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD INDEX `idx_organize_status` (`organize_status`)"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `is_deleted` TINYINT DEFAULT 0 AFTER `updated_at`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `deleted_at` DATETIME DEFAULT NULL AFTER `is_deleted`"));
    }

    @Test
    void addsOnlyMissingCaptureMetadataColumns() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        // Legacy base columns already present
        stubNoteColumnPresent(jdbcTemplate, "tags");
        stubNoteColumnPresent(jdbcTemplate, "is_pinned");
        stubNoteColumnPresent(jdbcTemplate, "is_deleted");
        stubNoteColumnPresent(jdbcTemplate, "deleted_at");
        // Capture columns missing
        stubNoteColumnMissing(jdbcTemplate, "note_type");
        stubNoteColumnMissing(jdbcTemplate, "organize_status");
        stubNoteColumnMissing(jdbcTemplate, "source_type");
        stubNoteColumnMissing(jdbcTemplate, "source_id");
        stubNoteColumnMissing(jdbcTemplate, "source_title");
        stubNoteColumnMissing(jdbcTemplate, "source_route");
        stubNoteColumnMissing(jdbcTemplate, "excerpt");
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "note", "idx_organize_status"))
                .thenReturn(0);

        runner.ensureNoteColumns();

        verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `note_type` VARCHAR(32) DEFAULT NULL COMMENT '摘录/速记/提问: excerpt|quick|question' AFTER `is_pinned`");
        verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `excerpt` TEXT DEFAULT NULL COMMENT '摘录原文（可为空）' AFTER `source_route`");
        verify(jdbcTemplate).execute("ALTER TABLE `note` ADD INDEX `idx_organize_status` (`organize_status`)");
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '标签数组' AFTER `content`"));
    }

    private static void stubNoteColumnMissing(JdbcTemplate jdbcTemplate, String column) {
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", column))
                .thenReturn(0);
    }

    private static void stubNoteColumnPresent(JdbcTemplate jdbcTemplate, String column) {
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", column))
                .thenReturn(1);
    }
}
