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
              AND table_name = 'user_profile'
              AND index_name = ?
            """;

    private final JdbcTemplate jdbcTemplate;

    @Override
    public void run(ApplicationArguments args) {
        fixUserProfileCurrentIndex();
    }

    void fixUserProfileCurrentIndex() {
        if (!indexExists("uk_user_current")) {
            return;
        }

        log.info("Migrating user_profile.uk_user_current from UNIQUE index to normal index");
        jdbcTemplate.execute("ALTER TABLE `user_profile` DROP INDEX `uk_user_current`");

        if (!indexExists("idx_user_current")) {
            jdbcTemplate.execute("ALTER TABLE `user_profile` ADD INDEX `idx_user_current` (`user_id`, `is_current`)");
        }
    }

    private boolean indexExists(String indexName) {
        Integer count = jdbcTemplate.queryForObject(INDEX_COUNT_SQL, Integer.class, indexName);
        return count != null && count > 0;
    }
}
