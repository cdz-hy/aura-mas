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
}
