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
}
