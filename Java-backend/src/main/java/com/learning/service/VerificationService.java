package com.learning.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class VerificationService {

    @Value("${verification.code-length:6}")
    private int codeLength;

    @Value("${verification.expire-seconds:300}")
    private long expireSeconds;

    @Value("${verification.cooldown-seconds:60}")
    private long cooldownSeconds;

    @Value("${verification.max-attempts:5}")
    private int maxAttempts;

    // IP 级限流：同一 IP 每小时最多发送 10 次验证码
    private static final int IP_HOURLY_LIMIT = 10;

    private final SecureRandom random = new SecureRandom();

    // Redis 可用性标记：启动时探测，不可用则全程降级为内存
    private volatile boolean redisAvailable = false;
    private final StringRedisTemplate redisTemplate;

    // 内存降级存储
    private final Map<String, MemCodeEntry> memCodeStore = new ConcurrentHashMap<>();
    private final Map<String, Long> memLastSendTime = new ConcurrentHashMap<>();
    private final Map<String, Integer> memAttemptCount = new ConcurrentHashMap<>();
    private final Map<String, Long> memIpSendCount = new ConcurrentHashMap<>();
    private final Map<String, Long> memIpWindowStart = new ConcurrentHashMap<>();

    private static class MemCodeEntry {
        String code;
        long expireAtMs;
        MemCodeEntry(String code, long expireAtMs) {
            this.code = code;
            this.expireAtMs = expireAtMs;
        }
        boolean isExpired() {
            return System.currentTimeMillis() > expireAtMs;
        }
    }

    public VerificationService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
        // 启动时探测 Redis 是否真正可用
        try {
            redisTemplate.getConnectionFactory().getConnection().ping();
            redisAvailable = true;
            log.info("[验证码] Redis 连接成功，使用 Redis 存储");
        } catch (Exception e) {
            redisAvailable = false;
            log.warn("[验证码] Redis 连接失败（{}），降级为内存存储", e.getMessage());
        }
    }

    /**
     * 生成并存储验证码。
     * @param email 目标邮箱
     * @param clientIp 客户端 IP（用于 IP 级限流）
     * @return null 表示成功，非 null 表示错误信息
     */
    public String generateCode(String email, String clientIp) {
        // IP 级限流
        String ipError = checkIpRateLimit(clientIp);
        if (ipError != null) return ipError;

        // 邮箱级限流：冷却时间
        String cooldownError = checkCooldown(email);
        if (cooldownError != null) return cooldownError;

        // 生成验证码
        String code = generateRandomCode();

        // 存储（Redis 优先，降级内存）
        if (redisAvailable) {
            try {
                storeRedis(email, code, clientIp);
            } catch (Exception e) {
                log.warn("[验证码] Redis 写入失败，降级内存: {}", e.getMessage());
                redisAvailable = false;
                storeMemory(email, code, clientIp);
            }
        } else {
            storeMemory(email, code, clientIp);
        }

        log.info("[验证码] 已生成: email={}, expire={}s", email, expireSeconds);
        return null;
    }

    /**
     * 验证验证码。
     * @return null 表示成功，否则返回错误信息
     */
    public String verifyCode(String email, String inputCode) {
        if (redisAvailable) {
            try {
                return verifyRedis(email, inputCode);
            } catch (Exception e) {
                log.warn("[验证码] Redis 读取失败，降级内存: {}", e.getMessage());
                redisAvailable = false;
                return verifyMemory(email, inputCode);
            }
        } else {
            return verifyMemory(email, inputCode);
        }
    }

    /**
     * 获取刚生成的验证码（供 EmailService 发送邮件时使用）
     */
    public String getLastGeneratedCode(String email) {
        if (redisAvailable) {
            try {
                return redisTemplate.opsForValue().get(keyCode(email));
            } catch (Exception e) {
                log.warn("[验证码] Redis 读取失败，降级内存: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        MemCodeEntry entry = memCodeStore.get(email);
        return (entry != null && !entry.isExpired()) ? entry.code : null;
    }

    // ==================== Redis 实现 ====================

    private void storeRedis(String email, String code, String clientIp) {
        redisTemplate.opsForValue().set(keyCode(email), code, Duration.ofSeconds(expireSeconds));
        redisTemplate.opsForValue().set(keyCooldown(email), "1", Duration.ofSeconds(cooldownSeconds));
        redisTemplate.opsForValue().set(keyAttempts(email), "0", Duration.ofSeconds(expireSeconds));
        // IP 限流计数
        redisTemplate.opsForValue().increment(keyIpCount(clientIp));
        redisTemplate.expire(keyIpCount(clientIp), Duration.ofHours(1));
    }

    private String verifyRedis(String email, String inputCode) {
        String storedCode = redisTemplate.opsForValue().get(keyCode(email));
        if (storedCode == null) {
            return "请先获取验证码";
        }

        // 尝试次数
        String attemptsStr = redisTemplate.opsForValue().get(keyAttempts(email));
        int attempts = attemptsStr != null ? Integer.parseInt(attemptsStr) : 0;
        if (attempts >= maxAttempts) {
            redisTemplate.delete(keyCode(email));
            redisTemplate.delete(keyAttempts(email));
            return "验证码尝试次数过多，请重新获取";
        }

        if (!storedCode.equals(inputCode.trim())) {
            redisTemplate.opsForValue().set(keyAttempts(email), String.valueOf(attempts + 1), Duration.ofSeconds(expireSeconds));
            int remaining = maxAttempts - attempts - 1;
            return "验证码错误，还可尝试 " + remaining + " 次";
        }

        // 验证成功，清理
        redisTemplate.delete(keyCode(email));
        redisTemplate.delete(keyAttempts(email));
        redisTemplate.delete(keyCooldown(email));
        log.info("[验证码] 验证成功: email={}", email);
        return null;
    }

    // ==================== 内存实现 ====================

    private void storeMemory(String email, String code, String clientIp) {
        memCodeStore.put(email, new MemCodeEntry(code, System.currentTimeMillis() + expireSeconds * 1000));
        memLastSendTime.put(email, System.currentTimeMillis());
        memAttemptCount.put(email, 0);
        // IP 限流计数
        memIpSendCount.merge(clientIp, 1L, Long::sum);
        memIpWindowStart.putIfAbsent(clientIp, System.currentTimeMillis());
    }

    private String verifyMemory(String email, String inputCode) {
        MemCodeEntry entry = memCodeStore.get(email);
        if (entry == null) {
            return "请先获取验证码";
        }
        if (entry.isExpired()) {
            memCodeStore.remove(email);
            memAttemptCount.remove(email);
            return "验证码已过期，请重新获取";
        }

        Integer attempts = memAttemptCount.getOrDefault(email, 0);
        if (attempts >= maxAttempts) {
            memCodeStore.remove(email);
            memAttemptCount.remove(email);
            return "验证码尝试次数过多，请重新获取";
        }

        if (!entry.code.equals(inputCode.trim())) {
            memAttemptCount.put(email, attempts + 1);
            int remaining = maxAttempts - attempts - 1;
            return "验证码错误，还可尝试 " + remaining + " 次";
        }

        // 验证成功
        memCodeStore.remove(email);
        memAttemptCount.remove(email);
        memLastSendTime.remove(email);
        log.info("[验证码] 验证成功: email={}", email);
        return null;
    }

    // ==================== IP 限流 ====================

    private String checkIpRateLimit(String clientIp) {
        if (clientIp == null || clientIp.isBlank()) return null;

        if (redisAvailable) {
            try {
                String countStr = redisTemplate.opsForValue().get(keyIpCount(clientIp));
                int count = countStr != null ? Integer.parseInt(countStr) : 0;
                if (count >= IP_HOURLY_LIMIT) {
                    return "该 IP 请求过于频繁，请稍后再试";
                }
            } catch (Exception e) {
                log.warn("[验证码] Redis IP限流查询失败，降级内存: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        if (!redisAvailable) {
            // 内存实现：滑动窗口 1 小时
            Long windowStart = memIpWindowStart.get(clientIp);
            if (windowStart != null) {
                long elapsed = System.currentTimeMillis() - windowStart;
                if (elapsed > 3600_000) {
                    memIpWindowStart.put(clientIp, System.currentTimeMillis());
                    memIpSendCount.put(clientIp, 0L);
                }
            }
            Long count = memIpSendCount.getOrDefault(clientIp, 0L);
            if (count >= IP_HOURLY_LIMIT) {
                return "该 IP 请求过于频繁，请稍后再试";
            }
        }
        return null;
    }

    // ==================== 邮箱级冷却 ====================

    private String checkCooldown(String email) {
        if (redisAvailable) {
            try {
                if (Boolean.TRUE.equals(redisTemplate.hasKey(keyCooldown(email)))) {
                    Long ttl = redisTemplate.getExpire(keyCooldown(email));
                    return "验证码发送过于频繁，请 " + (ttl != null ? ttl : cooldownSeconds) + " 秒后重试";
                }
            } catch (Exception e) {
                log.warn("[验证码] Redis 冷却查询失败，降级内存: {}", e.getMessage());
                redisAvailable = false;
            }
        }
        if (!redisAvailable) {
            Long lastSend = memLastSendTime.get(email);
            if (lastSend != null) {
                long elapsed = (System.currentTimeMillis() - lastSend) / 1000;
                if (elapsed < cooldownSeconds) {
                    return "验证码发送过于频繁，请 " + (cooldownSeconds - elapsed) + " 秒后重试";
                }
            }
        }
        return null;
    }

    // ==================== Redis Key 前缀 ====================

    private static String keyCode(String email) { return "verify:code:" + email; }
    private static String keyCooldown(String email) { return "verify:cd:" + email; }
    private static String keyAttempts(String email) { return "verify:att:" + email; }
    private static String keyIpCount(String ip) { return "verify:ip:" + ip; }

    private String generateRandomCode() {
        StringBuilder sb = new StringBuilder(codeLength);
        for (int i = 0; i < codeLength; i++) {
            sb.append(random.nextInt(10));
        }
        return sb.toString();
    }
}
