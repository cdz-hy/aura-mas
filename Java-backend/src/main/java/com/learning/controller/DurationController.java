package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.UserLearningProgress;
import com.learning.service.UserLearningProgressService;
import com.learning.util.AuthUtils;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "学习时长")
@RestController
@RequestMapping("/api/progress")
@RequiredArgsConstructor
public class DurationController {

    private final UserLearningProgressService progressService;

    @Operation(summary = "学习心跳上报")
    @PostMapping("/heartbeat")
    public Result<Void> heartbeat(
            Authentication authentication,
            @RequestParam Long planId,
            @RequestParam Long resourceId,
            @RequestParam int elapsedSeconds) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        progressService.heartbeat(userId, planId, resourceId, elapsedSeconds);
        return Result.success(null);
    }

    @Operation(summary = "标记资源完成")
    @PostMapping("/complete")
    public Result<Void> markComplete(
            Authentication authentication,
            @RequestParam Long planId,
            @RequestParam Long resourceId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        progressService.markComplete(userId, planId, resourceId);
        return Result.success(null);
    }

    @Operation(summary = "取消资源完成")
    @DeleteMapping("/complete")
    public Result<Void> unmarkComplete(
            Authentication authentication,
            @RequestParam Long planId,
            @RequestParam Long resourceId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        progressService.unmarkComplete(userId, planId, resourceId);
        return Result.success(null);
    }

    @Operation(summary = "获取计划下所有资源进度")
    @GetMapping("/plan")
    public Result<List<UserLearningProgress>> getByPlan(
            Authentication authentication,
            @RequestParam Long planId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(progressService.getByPlan(userId, planId));
    }

    @Operation(summary = "一键标记计划下所有已生成资源为完成")
    @PostMapping("/complete-all")
    public Result<Void> markAllComplete(
            Authentication authentication,
            @RequestParam Long planId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        progressService.markAllComplete(userId, planId);
        return Result.success(null);
    }

    @Operation(summary = "批量获取多个计划的进度摘要")
    @GetMapping("/batch")
    public Result<?> getBatchProgress(
            Authentication authentication,
            @RequestParam List<Long> planIds) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(progressService.getProgressSummary(userId, planIds));
    }

    @Operation(summary = "查询单个计划进度")
    @GetMapping("/plan/summary")
    public Result<?> getPlanProgress(
            Authentication authentication,
            @RequestParam Long planId) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        return Result.success(progressService.getPlanProgress(userId, planId));
    }
}
