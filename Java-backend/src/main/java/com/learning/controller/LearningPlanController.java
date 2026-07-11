package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.dto.PlanCreateRequest;
import com.learning.entity.LearningPlan;
import com.learning.service.LearningPlanService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@Slf4j
@Tag(name = "学习计划管理")
@RestController
@RequestMapping("/api/plan")
@RequiredArgsConstructor
public class LearningPlanController {

    private final LearningPlanService planService;

    @Operation(summary = "创建学习计划")
    @OperationLog(type = OperationType.PLAN_CREATE, module = "Plan",
            desc = "'创建学习计划: ' + #request.getTitle()",
            resourceId = "#result?.data?.id?.toString()")
    @PostMapping
    public Result<LearningPlan> createPlan(Authentication authentication,
                                            @Valid @RequestBody PlanCreateRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(planService.createPlan(userId, request));
    }

    @Operation(summary = "获取学习计划详情")
    @GetMapping("/{planId}")
    public Result<LearningPlan> getPlan(Authentication authentication,
                                         @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(planService.getPlanById(planId, userId));
    }

    @Operation(summary = "获取用户学习计划列表")
    @GetMapping("/list")
    public Result<PageResult<LearningPlan>> getPlans(Authentication authentication,
                                                      @RequestParam(defaultValue = "1") int page,
                                                      @RequestParam(defaultValue = "10") int size) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(planService.getUserPlans(userId, page, size));
    }

    @Operation(summary = "更新学习计划")
    @OperationLog(type = OperationType.PLAN_UPDATE, module = "Plan",
            desc = "'更新学习计划ID: ' + #planId",
            resourceId = "#planId?.toString()")
    @PutMapping("/{planId}")
    public Result<LearningPlan> updatePlan(Authentication authentication,
                                            @PathVariable Long planId,
                                            @Valid @RequestBody PlanCreateRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(planService.updatePlan(planId, userId, request));
    }

    @Operation(summary = "删除学习计划")
    @OperationLog(type = OperationType.PLAN_DELETE, module = "Plan",
            desc = "'删除学习计划ID: ' + #planId",
            resourceId = "#planId?.toString()")
    @DeleteMapping("/{planId}")
    public Result<Void> deletePlan(Authentication authentication,
                                    @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        planService.deletePlan(planId, userId);
        return Result.success();
    }

    @Operation(summary = "更新计划状态")
    @OperationLog(type = OperationType.PLAN_STATUS_CHANGE, module = "Plan",
            desc = "'更新计划状态ID: ' + #planId + ' -> ' + #status",
            resourceId = "#planId?.toString()")
    @PutMapping("/{planId}/status")
    public Result<Void> updatePlanStatus(@PathVariable Long planId,
                                          @RequestParam Integer status) {
        planService.updatePlanStatus(planId, status);
        return Result.success();
    }

    @Operation(summary = "内部接口：创建学习计划")
    @PostMapping("/internal/create")
    public Result<LearningPlan> createPlanInternal(@RequestBody java.util.Map<String, Object> body) {
        Long userId = Long.valueOf(body.get("userId").toString());
        String title = (String) body.get("title");
        Object learningGoal = body.get("learningGoal");
        Object planConfig = body.get("planConfig");
        Integer status = body.get("status") != null ? Integer.valueOf(body.get("status").toString()) : null;
        return Result.success(planService.createPlanInternal(userId, title, learningGoal, planConfig, status));
    }

    @Operation(summary = "内部接口：获取计划详情")
    @GetMapping("/internal/{planId}")
    public Result<LearningPlan> getPlanInternal(@PathVariable Long planId) {
        return Result.success(planService.getPlanByIdInternal(planId));
    }

    @Operation(summary = "内部接口：会话级 learning_goal 增量更新（保留演进历史）")
    @PatchMapping("/internal/{planId}/learning-goal")
    public Result<Void> upsertSessionLearningGoal(@PathVariable Long planId,
                                                   @RequestBody java.util.Map<String, Object> body) {
        String sessionId = (String) body.get("sessionId");
        String goal = (String) body.get("goal");
        String action = body.get("action") != null ? body.get("action").toString() : "update";
        String reasoning = body.get("reasoning") != null ? body.get("reasoning").toString() : "";
        if (sessionId == null || sessionId.isEmpty() || goal == null || goal.isEmpty()) {
            return Result.success();
        }
        planService.upsertSessionLearningGoal(planId, sessionId, goal, action, reasoning);
        return Result.success();
    }

    @Operation(summary = "内部接口：更新计划配置")
    @PutMapping("/internal/{planId}/config")
    public Result<Void> updatePlanConfigInternal(@PathVariable Long planId,
                                                  @RequestBody java.util.Map<String, Object> body) {
        Object planConfig = body.get("planConfig");
        if (planConfig != null) {
            planService.updatePlanConfig(planId, planConfig);
        }
        return Result.success();
    }

    @Operation(summary = "内部接口：调整计划（加速/减速/重排等）")
    @PostMapping("/internal/{planId}/adjust")
    public Result<Void> adjustPlanInternal(@PathVariable Long planId,
                                            @RequestBody java.util.Map<String, Object> body) {
        String action = (String) body.get("action");
        String reason = (String) body.get("reason");
        @SuppressWarnings("unchecked")
        java.util.List<String> modules = (java.util.List<String>) body.get("modules_to_adjust");

        // 这里可以根据 action 执行不同的调整逻辑
        // 例如：accelerate, decelerate, reorder, add_review, skip
        log.info("[计划调整] planId={}, action={}, reason={}, modules={}", planId, action, reason, modules);

        // 目前只记录日志，后续可以实现具体的调整逻辑
        return Result.success();
    }
}
