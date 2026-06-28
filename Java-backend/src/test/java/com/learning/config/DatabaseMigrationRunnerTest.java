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

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "uk_user_current"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "idx_user_current"))
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

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "uk_user_current"))
                .thenReturn(0);

        runner.fixUserProfileCurrentIndex();

        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)"));
    }

    @Test
    void doesNotCreateDuplicateNormalIndexWhenItAlreadyExists() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "uk_user_current"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.INDEX_COUNT_SQL, Integer.class, "idx_user_current"))
                .thenReturn(1);

        runner.fixUserProfileCurrentIndex();

        verify(jdbcTemplate).execute("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`");
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)"));
    }

    @Test
    void addsMissingNoteColumnsForLegacyTables() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "tags"))
                .thenReturn(0);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "is_pinned"))
                .thenReturn(0);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "is_deleted"))
                .thenReturn(0);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "deleted_at"))
                .thenReturn(0);

        runner.ensureNoteColumns();

        var inOrder = inOrder(jdbcTemplate);
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '标签数组' AFTER `content`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `is_pinned` TINYINT DEFAULT 0 COMMENT '是否置顶' AFTER `tags`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `is_deleted` TINYINT DEFAULT 0 AFTER `updated_at`");
        inOrder.verify(jdbcTemplate).execute("ALTER TABLE `note` ADD COLUMN `deleted_at` DATETIME DEFAULT NULL AFTER `is_deleted`");
    }

    @Test
    void doesNotAddExistingNoteColumns() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        DatabaseMigrationRunner runner = new DatabaseMigrationRunner(jdbcTemplate);

        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "tags"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "is_pinned"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "is_deleted"))
                .thenReturn(1);
        when(jdbcTemplate.queryForObject(DatabaseMigrationRunner.COLUMN_COUNT_SQL, Integer.class, "note", "deleted_at"))
                .thenReturn(1);

        runner.ensureNoteColumns();

        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '标签数组' AFTER `content`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `is_pinned` TINYINT DEFAULT 0 COMMENT '是否置顶' AFTER `tags`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `is_deleted` TINYINT DEFAULT 0 AFTER `updated_at`"));
        verify(jdbcTemplate, never()).execute(eq("ALTER TABLE `note` ADD COLUMN `deleted_at` DATETIME DEFAULT NULL AFTER `is_deleted`"));
    }
}
