package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.LearningStrategy;
import com.learning.service.LearningTrackerService;
import com.learning.util.AuthUtils;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "学习追踪")
@RestController
@RequestMapping("/api/tracker")
@RequiredArgsConstructor
public class LearningTrackerController {

    private final LearningTrackerService trackerService;

    @Operation(summary = "批量上报学习事件")
    @PostMapping("/events")
    public Result<Void> trackEvents(Authentication authentication,
                                     @RequestBody List<Map<String, Object>> events) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        trackerService.saveEvents(userId, events);
        return Result.success();
    }

    @Operation(summary = "内部接口：批量上报学习事件")
    @PostMapping("/internal/events")
    public Result<Void> trackEventsInternal(@RequestParam Long userId,
                                             @RequestBody List<Map<String, Object>> events) {
        trackerService.saveEvents(userId, events);
        return Result.success();
    }

    @Operation(summary = "获取待处理策略数量")
    @GetMapping("/strategies/count")
    public Result<Integer> getPendingStrategyCount(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(trackerService.getPendingStrategyCount(userId));
    }

    @Operation(summary = "获取待处理策略列表")
    @GetMapping("/strategies/pending")
    public Result<List<LearningStrategy>> getPendingStrategies(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(trackerService.getPendingStrategies(userId));
    }

    @Operation(summary = "获取用户策略列表")
    @GetMapping("/strategies")
    public Result<List<LearningStrategy>> getUserStrategies(
            Authentication authentication,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "20") int limit) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(trackerService.getUserStrategies(userId, status, limit));
    }

    @Operation(summary = "接受策略")
    @PostMapping("/strategies/{strategyId}/accept")
    public Result<Boolean> acceptStrategy(Authentication authentication,
                                           @PathVariable Long strategyId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(trackerService.acceptStrategy(strategyId, userId));
    }

    @Operation(summary = "拒绝策略")
    @PostMapping("/strategies/{strategyId}/reject")
    public Result<Boolean> rejectStrategy(Authentication authentication,
                                           @PathVariable Long strategyId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(trackerService.rejectStrategy(strategyId, userId));
    }

    @Operation(summary = "内部接口：获取用户最近事件")
    @GetMapping("/internal/events")
    public Result<?> getRecentEvents(@RequestParam Long userId,
                                      @RequestParam(defaultValue = "5") int hours) {
        return Result.success(trackerService.getRecentEvents(userId, hours));
    }

    @Operation(summary = "内部接口：获取今日学习时长")
    @GetMapping("/internal/today-duration")
    public Result<Integer> getTodayStudyDuration(@RequestParam Long userId) {
        return Result.success(trackerService.getTodayStudyDuration(userId));
    }

    @Operation(summary = "内部接口：保存策略")
    @PostMapping("/internal/strategies")
    public Result<LearningStrategy> saveStrategy(
            @RequestParam Long userId,
            @RequestParam String strategyType,
            @RequestParam String title,
            @RequestParam String description,
            @RequestBody Map<String, Object> strategyData,
            @RequestParam(defaultValue = "72") int expireHours) {
        return Result.success(trackerService.saveStrategy(
                userId, strategyType, title, description, strategyData, expireHours));
    }

    @Operation(summary = "内部接口：清理过期策略")
    @PostMapping("/internal/clean-expired")
    public Result<Integer> cleanExpiredStrategies() {
        return Result.success(trackerService.cleanExpiredStrategies());
    }

    @Operation(summary = "内部接口：获取有学习事件的活跃用户ID列表")
    @GetMapping("/internal/active-users")
    public Result<?> getActiveUsers(@RequestParam(defaultValue = "5") int hours) {
        return Result.success(trackerService.getActiveUserIds(hours));
    }

    @Operation(summary = "用户心跳 - 追踪活跃时间")
    @PostMapping("/heartbeat")
    public Result<Void> heartbeat(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        trackerService.recordHeartbeat(userId);
        return Result.success();
    }

    @Operation(summary = "内部接口：检查用户是否需要分析")
    @GetMapping("/internal/need-analysis")
    public Result<Boolean> needAnalysis(@RequestParam Long userId) {
        return Result.success(trackerService.needAnalysis(userId));
    }

    @Operation(summary = "内部接口：清空用户的待处理策略")
    @PostMapping("/internal/clear-user-strategies")
    public Result<Integer> clearUserStrategies(@RequestParam Long userId) {
        return Result.success(trackerService.clearPendingStrategies(userId));
    }
}
