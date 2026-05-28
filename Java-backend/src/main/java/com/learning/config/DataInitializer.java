package com.learning.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final JdbcTemplate jdbcTemplate;

    @Override
    public void run(String... args) {
        ensureIndex("ai_token_usage", "idx_created_at", "created_at");
    }

    private void ensureIndex(String table, String indexName, String column) {
        try {
            Integer count = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM information_schema.statistics " +
                    "WHERE table_schema = DATABASE() AND table_name = ? AND index_name = ?",
                    Integer.class, table, indexName);
            if (count != null && count == 0) {
                jdbcTemplate.execute("ALTER TABLE `" + table + "` ADD KEY `" + indexName + "` (`" + column + "`)");
                log.info("Auto-created index {} on {}.{}", indexName, table, column);
            }
        } catch (Exception e) {
            log.warn("Failed to ensure index {} on {}: {}", indexName, table, e.getMessage());
        }
    }
}
