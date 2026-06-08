package com.learning.controller;

import com.learning.common.Result;
import com.learning.service.StatsService;
import com.learning.util.AuthUtils;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@Tag(name = "统计管理")
@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {

    private final StatsService statsService;

    @Operation(summary = "获取仪表盘统计数据")
    @GetMapping("/dashboard")
    public Result<Map<String, Object>> getDashboard(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getDashboardStats(userId));
    }

    @Operation(summary = "获取答题详细分析")
    @GetMapping("/quiz-analysis")
    public Result<Map<String, Object>> getQuizAnalysis(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getQuizAnalysis(userId));
    }

    @Operation(summary = "获取学习热力图数据")
    @GetMapping("/study-heatmap")
    public Result<Map<String, Object>> getStudyHeatmap(
            Authentication authentication,
            @RequestParam(defaultValue = "180") int days) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getStudyHeatmap(userId, days));
    }

    @Operation(summary = "获取闪卡复习统计")
    @GetMapping("/flashcard-stats")
    public Result<Map<String, Object>> getFlashcardStats(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getFlashcardStats(userId));
    }

    @Operation(summary = "获取AI对话分析")
    @GetMapping("/ai-interaction")
    public Result<Map<String, Object>> getAiInteraction(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getAiInteractionStats(userId));
    }

    @Operation(summary = "获取知识掌握度")
    @GetMapping("/knowledge-mastery")
    public Result<Map<String, Object>> getKnowledgeMastery(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getKnowledgeMastery(userId));
    }

    @Operation(summary = "获取全部分析数据")
    @GetMapping("/analytics")
    public Result<Map<String, Object>> getAnalytics(Authentication authentication) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(statsService.getAnalyticsData(userId));
    }
}
