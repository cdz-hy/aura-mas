package com.learning.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DatabaseMigrationRunner implements ApplicationRunner {

    static final String INDEX_COUNT_SQL = """
            SELECT COUNT(*)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = ?
              AND index_name = ?
            """;

    static final String COLUMN_COUNT_SQL = """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = ?
              AND column_name = ?
            """;

    private final JdbcTemplate jdbcTemplate;

    @Override
    public void run(ApplicationArguments args) {
        fixUserProfileCurrentIndex();
        ensureNoteColumns();
        ensureSystemLogColumns();
        ensureLogManagementMenu();
    }

    void fixUserProfileCurrentIndex() {
        if (!indexExists("user_profile", "uk_user_current")) {
            return;
        }

        log.info("Migrating user_profile.uk_user_current from UNIQUE index to normal index");
        jdbcTemplate.execute("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`");

        if (!indexExists("user_profile", "idx_user_current")) {
            jdbcTemplate.execute("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)");
        }
    }

    void ensureSystemLogColumns() {
        if (!columnExists("system_log", "operation_desc")) {
            jdbcTemplate.execute("ALTER TABLE `system_log` ADD COLUMN `operation_desc` VARCHAR(200) DEFAULT NULL COMMENT '操作描述' AFTER `operation_type`");
        }
        if (!columnExists("system_log", "module")) {
            jdbcTemplate.execute("ALTER TABLE `system_log` ADD COLUMN `module` VARCHAR(50) DEFAULT NULL COMMENT '所属模块' AFTER `operation_desc`");
        }
        if (!columnExists("system_log", "status")) {
            jdbcTemplate.execute("ALTER TABLE `system_log` ADD COLUMN `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1=成功 0=失败' AFTER `user_ip`");
        }
        if (!columnExists("system_log", "error_msg")) {
            jdbcTemplate.execute("ALTER TABLE `system_log` ADD COLUMN `error_msg` VARCHAR(500) DEFAULT NULL COMMENT '失败原因' AFTER `status`");
        }
        if (!indexExists("system_log", "idx_created_at")) {
            jdbcTemplate.execute("ALTER TABLE `system_log` ADD INDEX `idx_created_at` (`created_at`)");
        }
    }

    void ensureLogManagementMenu() {
        Integer count = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM menu WHERE code = 'log-management'", Integer.class);
        if (count != null && count == 0) {
            log.info("Inserting log-management menu entry");
            jdbcTemplate.execute("""
                    INSERT INTO menu (code, name, path, icon, type, sort_order)
                    VALUES ('log-management', '系统日志', '/admin/logs', 'log', 'menu', 105)
                    """);
            jdbcTemplate.execute("""
                    INSERT IGNORE INTO role_menu (role, menu_id)
                    SELECT 'admin', id FROM menu WHERE code = 'log-management'
                    """);
        }
    }

    void ensureNoteColumns() {
        if (!columnExists("note", "tags")) {
            jdbcTemplate.execute("ALTER TABLE `note` ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '标签数组' AFTER `content`");
        }
        if (!columnExists("note", "is_pinned")) {
            jdbcTemplate.execute("ALTER TABLE `note` ADD COLUMN `is_pinned` TINYINT DEFAULT 0 COMMENT '是否置顶' AFTER `tags`");
        }
        if (!columnExists("note", "is_deleted")) {
            jdbcTemplate.execute("ALTER TABLE `note` ADD COLUMN `is_deleted` TINYINT DEFAULT 0 AFTER `updated_at`");
        }
        if (!columnExists("note", "deleted_at")) {
            jdbcTemplate.execute("ALTER TABLE `note` ADD COLUMN `deleted_at` DATETIME DEFAULT NULL AFTER `is_deleted`");
        }
    }

    private boolean indexExists(String tableName, String indexName) {
        Integer count = jdbcTemplate.queryForObject(INDEX_COUNT_SQL, Integer.class, tableName, indexName);
        return count != null && count > 0;
    }

    private boolean columnExists(String tableName, String columnName) {
        Integer count = jdbcTemplate.queryForObject(COLUMN_COUNT_SQL, Integer.class, tableName, columnName);
        return count != null && count > 0;
    }
}
