package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.entity.LearningEvent;
import com.learning.entity.LearningStrategy;
import com.learning.mapper.LearningEventMapper;
import com.learning.mapper.LearningStrategyMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class LearningTrackerService {

    private final LearningEventMapper eventMapper;
    private final LearningStrategyMapper strategyMapper;
    private final ObjectMapper objectMapper;

    /**
     * 保存学习事件
     */
    @Transactional
    public void saveEvents(Long userId, List<Map<String, Object>> events) {
        // 限制单次上报数量
        int maxSize = 100;
        if (events.size() > maxSize) {
            log.warn("[学习追踪] 事件数量超限: {} > {}, 截断", events.size(), maxSize);
            events = events.subList(0, maxSize);
        }

        for (Map<String, Object> event : events) {
            LearningEvent entity = new LearningEvent();
            entity.setUserId(userId);
            entity.setEventType((String) event.get("eventType"));
            entity.setCreatedAt(LocalDateTime.now());
            try {
                entity.setEventData(objectMapper.writeValueAsString(event.get("data")));
            } catch (Exception e) {
                entity.setEventData("{}");
            }
            eventMapper.insert(entity);
        }
        log.info("[学习追踪] 保存 {} 条事件, userId={}", events.size(), userId);
    }

    /**
     * 获取用户最近的学习事件
     */
    public List<LearningEvent> getRecentEvents(Long userId, int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        return eventMapper.selectList(
                new LambdaQueryWrapper<LearningEvent>()
                        .eq(LearningEvent::getUserId, userId)
                        .ge(LearningEvent::getCreatedAt, since)
                        .orderByDesc(LearningEvent::getCreatedAt)
        );
    }

    /**
     * 获取用户今日学习时长（秒）
     */
    public int getTodayStudyDuration(Long userId) {
        LocalDateTime todayStart = LocalDateTime.now().toLocalDate().atStartOfDay();
        List<LearningEvent> events = eventMapper.selectList(
                new LambdaQueryWrapper<LearningEvent>()
                        .eq(LearningEvent::getUserId, userId)
                        .eq(LearningEvent::getEventType, "page_view")
                        .ge(LearningEvent::getCreatedAt, todayStart)
        );
        int totalSeconds = 0;
        for (LearningEvent event : events) {
            try {
                Map<String, Object> data = objectMapper.readValue(event.getEventData(), Map.class);
                if (data.containsKey("duration")) {
                    totalSeconds += ((Number) data.get("duration")).intValue();
                }
            } catch (Exception ignored) {
            }
        }
        return totalSeconds;
    }

    /**
     * 保存学习策略
     */
    @Transactional
    public LearningStrategy saveStrategy(Long userId, String strategyType, String title,
                                          String description, Map<String, Object> strategyData,
                                          int expireHours) {
        LearningStrategy entity = new LearningStrategy();
        entity.setUserId(userId);
        entity.setStrategyType(strategyType);
        entity.setTitle(title);
        entity.setDescription(description);
        try {
            entity.setStrategyData(objectMapper.writeValueAsString(strategyData));
        } catch (Exception e) {
            entity.setStrategyData("{}");
        }
        entity.setStatus("pending");
        entity.setCreatedAt(LocalDateTime.now());
        entity.setExpiresAt(LocalDateTime.now().plusHours(expireHours));
        strategyMapper.insert(entity);
        log.info("[学习策略] 保存策略: id={}, type={}, userId={}", entity.getId(), strategyType, userId);
        return entity;
    }

    /**
     * 获取用户的待处理策略
     */
    public List<LearningStrategy> getPendingStrategies(Long userId) {
        return strategyMapper.selectList(
                new LambdaQueryWrapper<LearningStrategy>()
                        .eq(LearningStrategy::getUserId, userId)
                        .eq(LearningStrategy::getStatus, "pending")
                        .ge(LearningStrategy::getExpiresAt, LocalDateTime.now())
                        .orderByDesc(LearningStrategy::getCreatedAt)
        );
    }

    /**
     * 获取用户的策略列表
     */
    public List<LearningStrategy> getUserStrategies(Long userId, String status, int limit) {
        LambdaQueryWrapper<LearningStrategy> wrapper = new LambdaQueryWrapper<LearningStrategy>()
                .eq(LearningStrategy::getUserId, userId);
        if (status != null && !status.isEmpty()) {
            wrapper.eq(LearningStrategy::getStatus, status);
        }
        wrapper.orderByDesc(LearningStrategy::getCreatedAt)
                .last("LIMIT " + Math.min(limit, 100)); // 限制最大100条
        return strategyMapper.selectList(wrapper);
    }

    /**
     * 接受策略
     */
    @Transactional
    public boolean acceptStrategy(Long strategyId, Long userId) {
        LearningStrategy strategy = strategyMapper.selectById(strategyId);
        if (strategy == null || !strategy.getUserId().equals(userId)) {
            return false;
        }
        strategy.setStatus("accepted");
        strategy.setAcceptedAt(LocalDateTime.now());
        strategyMapper.updateById(strategy);
        log.info("[学习策略] 策略已接受: id={}", strategyId);
        return true;
    }

    /**
     * 拒绝策略
     */
    @Transactional
    public boolean rejectStrategy(Long strategyId, Long userId) {
        LearningStrategy strategy = strategyMapper.selectById(strategyId);
        if (strategy == null || !strategy.getUserId().equals(userId)) {
            return false;
        }
        strategy.setStatus("rejected");
        strategyMapper.updateById(strategy);
        log.info("[学习策略] 策略已拒绝: id={}", strategyId);
        return true;
    }

    /**
     * 获取待处理策略数量
     */
    public int getPendingStrategyCount(Long userId) {
        Long count = strategyMapper.selectCount(
                new LambdaQueryWrapper<LearningStrategy>()
                        .eq(LearningStrategy::getUserId, userId)
                        .eq(LearningStrategy::getStatus, "pending")
                        .ge(LearningStrategy::getExpiresAt, LocalDateTime.now())
        );
        return count != null ? count.intValue() : 0;
    }

    /**
     * 清理过期策略
     */
    @Transactional
    public int cleanExpiredStrategies() {
        return strategyMapper.delete(
                new LambdaQueryWrapper<LearningStrategy>()
                        .lt(LearningStrategy::getExpiresAt, LocalDateTime.now())
                        .eq(LearningStrategy::getStatus, "pending")
        );
    }

    /**
     * 获取最近有学习事件的活跃用户ID列表
     */
    public List<Long> getActiveUserIds(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<LearningEvent> events = eventMapper.selectList(
                new LambdaQueryWrapper<LearningEvent>()
                        .select(LearningEvent::getUserId)
                        .ge(LearningEvent::getCreatedAt, since)
                        .groupBy(LearningEvent::getUserId)
        );
        return events.stream()
                .map(LearningEvent::getUserId)
                .distinct()
                .collect(java.util.stream.Collectors.toList());
    }

    /**
     * 记录用户心跳（每分钟调用一次）
     * 使用 learning_events 表记录心跳事件
     */
    public void recordHeartbeat(Long userId) {
        try {
            // 保存心跳事件到数据库
            LearningEvent event = new LearningEvent();
            event.setUserId(userId);
            event.setEventType("heartbeat");
            event.setEventData("{}");
            event.setCreatedAt(LocalDateTime.now());
            eventMapper.insert(event);
            log.debug("[学习追踪] 用户 {} 心跳已记录", userId);
        } catch (Exception e) {
            log.warn("[学习追踪] 记录心跳失败: {}", e.getMessage());
        }
    }

    /**
     * 检查用户是否需要进行学习分析
     * 基于用户的活跃时间（累计5小时）
     */
    public boolean needAnalysis(Long userId) {
        // 获取用户最近的学习事件（包括心跳）
        LocalDateTime since = LocalDateTime.now().minusHours(24);
        List<LearningEvent> events = eventMapper.selectList(
                new LambdaQueryWrapper<LearningEvent>()
                        .eq(LearningEvent::getUserId, userId)
                        .ge(LearningEvent::getCreatedAt, since)
                        .in(LearningEvent::getEventType, "heartbeat", "page_view", "resource_view")
        );

        if (events.size() < 2) {
            return false;
        }

        // 计算活跃时间（基于事件间隔）
        long activeMinutes = calculateActiveMinutes(events);

        // 检查是否已超过5小时（300分钟）
        boolean needAnalysis = activeMinutes >= 300;

        if (needAnalysis) {
            log.info("[学习追踪] 用户 {} 活跃时间达到 {} 分钟，需要分析", userId, activeMinutes);
        }

        return needAnalysis;
    }

    /**
     * 计算用户的活跃时间（基于事件间隔）
     */
    private long calculateActiveMinutes(List<LearningEvent> events) {
        if (events.size() < 2) {
            return 0;
        }

        // 按时间排序
        events.sort((a, b) -> a.getCreatedAt().compareTo(b.getCreatedAt()));

        long activeMs = 0;
        LocalDateTime lastEventTime = null;

        for (LearningEvent event : events) {
            LocalDateTime currentTime = event.getCreatedAt();
            if (lastEventTime != null) {
                long gapMs = java.time.Duration.between(lastEventTime, currentTime).toMillis();
                // 如果间隔小于5分钟，算作活跃时间
                if (gapMs <= 5 * 60 * 1000) {
                    activeMs += gapMs;
                }
            }
            lastEventTime = currentTime;
        }

        return activeMs / (60 * 1000); // 转换为分钟
    }

    /**
     * 清空用户的待处理策略
     */
    @Transactional
    public int clearPendingStrategies(Long userId) {
        int count = strategyMapper.delete(
                new LambdaQueryWrapper<LearningStrategy>()
                        .eq(LearningStrategy::getUserId, userId)
                        .eq(LearningStrategy::getStatus, "pending")
        );
        log.info("[学习策略] 清空用户 {} 的待处理策略: {} 条", userId, count);
        return count;
    }
}
