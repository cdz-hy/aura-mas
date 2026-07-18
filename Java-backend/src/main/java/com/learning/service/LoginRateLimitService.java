package com.learning.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class LoginRateLimitService {

    // 账号级：5 次失败后锁定 15 分钟
    private static final int ACCOUNT_MAX_ATTEMPTS = 5;
    private static final long ACCOUNT_LOCK_SECONDS = 900; // 15 min

    // IP 级：每小时最多 30 次登录尝试
    private static final int IP_HOURLY_LIMIT = 30;

    private volatile boolean redisAvailable = false;
    private final StringRedisTemplate redisTemplate;

    // 内存降级
    private final Map<String, Integer> memAccountAttempts = new ConcurrentHashMap<>();
    private final Map<String, Long> memAccountLockUntil = new ConcurrentHashMap<>();
    private final Map<String, Integer> memIpAttempts = new ConcurrentHashMap<>();
    private final Map<String, Long> memIpWindowStart = new ConcurrentHashMap<>();

    public LoginRateLimitService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
        try {
            redisTemplate.getConnectionFactory().getConnection().ping();
            redisAvailable = true;
        } catch (Exception e) {
            redisAvailable = false;
            log.warn("[登录限流] Redis 不可用，降级为内存: {}", e.getMessage());
        }
    }

    /**
     * 检查登录是否被限流。返回 null 表示允许，否则返回错误信息。
     */
    public String checkLimit(String loginName, String clientIp) {
        // 1. 账号级锁定检查
        String accountError = checkAccountLock(loginName);
        if (accountError != null) return accountError;

        // 2. IP 级限流检查
        String ipError = checkIpLimit(clientIp);
        if (ipError != null) return ipError;

        return null;
    }

    /**
     * 记录一次登录失败。
     */
    public void recordFailure(String loginName, String clientIp) {
        if (redisAvailable) {
            try {
                String key = keyAccountAttempts(loginName);
                redisTemplate.opsForValue().increment(key);
                redisTemplate.expire(key, Duration.ofSeconds(ACCOUNT_LOCK_SECONDS));
                // 检查是否达到锁定阈值
                String countStr = redisTemplate.opsForValue().get(key);
                int count = countStr != null ? Integer.parseInt(countStr) : 0;
                if (count >= ACCOUNT_MAX_ATTEMPTS) {
                    redisTemplate.opsForValue().set(keyAccountLock(loginName), "1", Duration.ofSeconds(ACCOUNT_LOCK_SECONDS));
                    log.warn("[登录限流] 账号 {} 已被锁定 {} 秒", loginName, ACCOUNT_LOCK_SECONDS);
                }
            } catch (Exception e) {
                log.warn("[登录限流] Redis 写入失败: {}", e.getMessage());
                redisAvailable = false;
                recordFailureMemory(loginName);
            }
        } else {
            recordFailureMemory(loginName);
        }
    }

    /**
     * 登录成功后清除该账号的失败计数。
     */
    public void clearFailures(String loginName) {
        if (redisAvailable) {
            try {
                redisTemplate.delete(keyAccountAttempts(loginName));
                redisTemplate.delete(keyAccountLock(loginName));
            } catch (Exception e) {
                redisAvailable = false;
                memAccountAttempts.remove(loginName);
                memAccountLockUntil.remove(loginName);
            }
        } else {
            memAccountAttempts.remove(loginName);
            memAccountLockUntil.remove(loginName);
        }
    }

    // ==================== 账号级限流 ====================

    private String checkAccountLock(String loginName) {
        if (redisAvailable) {
            try {
                if (Boolean.TRUE.equals(redisTemplate.hasKey(keyAccountLock(loginName)))) {
                    Long ttl = redisTemplate.getExpire(keyAccountLock(loginName));
                    long seconds = ttl != null && ttl > 0 ? ttl : ACCOUNT_LOCK_SECONDS;
                    return "登录失败次数过多，账号已锁定 " + (seconds / 60) + " 分钟";
                }
            } catch (Exception e) {
                redisAvailable = false;
            }
        }
        if (!redisAvailable) {
            Long lockUntil = memAccountLockUntil.get(loginName);
            if (lockUntil != null && System.currentTimeMillis() < lockUntil) {
                long remaining = (lockUntil - System.currentTimeMillis()) / 1000;
                return "登录失败次数过多，账号已锁定 " + (remaining / 60 + 1) + " 分钟";
            }
        }
        return null;
    }

    private void recordFailureMemory(String loginName) {
        int attempts = memAccountAttempts.getOrDefault(loginName, 0) + 1;
        memAccountAttempts.put(loginName, attempts);
        if (attempts >= ACCOUNT_MAX_ATTEMPTS) {
            memAccountLockUntil.put(loginName, System.currentTimeMillis() + ACCOUNT_LOCK_SECONDS * 1000);
            log.warn("[登录限流] 账号 {} 已被锁定 {} 秒（内存）", loginName, ACCOUNT_LOCK_SECONDS);
        }
    }

    // ==================== IP 级限流 ====================

    private String checkIpLimit(String clientIp) {
        if (clientIp == null || clientIp.isBlank()) return null;

        if (redisAvailable) {
            try {
                String countStr = redisTemplate.opsForValue().get(keyIpAttempts(clientIp));
                int count = countStr != null ? Integer.parseInt(countStr) : 0;
                if (count >= IP_HOURLY_LIMIT) {
                    return "该 IP 登录请求过于频繁，请稍后再试";
                }
                // 不在这里 increment，由调用方在登录失败时 increment
            } catch (Exception e) {
                redisAvailable = false;
            }
        }
        if (!redisAvailable) {
            Long windowStart = memIpWindowStart.get(clientIp);
            if (windowStart != null) {
                long elapsed = System.currentTimeMillis() - windowStart;
                if (elapsed > 3600_000) {
                    memIpWindowStart.put(clientIp, System.currentTimeMillis());
                    memIpAttempts.put(clientIp, 0);
                }
            }
            int count = memIpAttempts.getOrDefault(clientIp, 0);
            if (count >= IP_HOURLY_LIMIT) {
                return "该 IP 登录请求过于频繁，请稍后再试";
            }
        }
        return null;
    }

    /**
     * 记录一次 IP 级登录尝试（无论成功失败）。
     */
    public void recordIpAttempt(String clientIp) {
        if (clientIp == null || clientIp.isBlank()) return;
        if (redisAvailable) {
            try {
                redisTemplate.opsForValue().increment(keyIpAttempts(clientIp));
                redisTemplate.expire(keyIpAttempts(clientIp), Duration.ofHours(1));
            } catch (Exception e) {
                redisAvailable = false;
                memIpAttempts.merge(clientIp, 1, Integer::sum);
                memIpWindowStart.putIfAbsent(clientIp, System.currentTimeMillis());
            }
        } else {
            memIpAttempts.merge(clientIp, 1, Integer::sum);
            memIpWindowStart.putIfAbsent(clientIp, System.currentTimeMillis());
        }
    }

    // ==================== Redis Key ====================

    private static String keyAccountAttempts(String loginName) { return "login:att:" + loginName; }
    private static String keyAccountLock(String loginName) { return "login:lock:" + loginName; }
    private static String keyIpAttempts(String ip) { return "login:ip:" + ip; }
}
