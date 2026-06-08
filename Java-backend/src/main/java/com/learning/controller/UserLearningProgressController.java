package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.UserLearningProgress;
import com.learning.service.UserLearningProgressService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "学习进度")
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class UserLearningProgressController {

    private final UserLearningProgressService progressService;

    @Operation(summary = "获取计划下的学习进度")
    @GetMapping("/progress/plan/{planId}")
    public Result<List<UserLearningProgress>> getProgressByPlan(
            Authentication authentication,
            @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(progressService.getByPlan(userId, planId));
    }

    @Operation(summary = "内部接口：获取计划下的学习进度")
    @GetMapping("/internal/progress/plan/{planId}")
    public Result<List<UserLearningProgress>> getProgressByPlanInternal(
            @PathVariable Long planId,
            @RequestParam Long userId) {
        return Result.success(progressService.getByPlan(userId, planId));
    }
}
