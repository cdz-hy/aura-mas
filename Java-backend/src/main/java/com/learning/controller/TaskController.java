package com.learning.controller;

import com.learning.common.Result;
import com.learning.dto.TaskDispatchRequest;
import com.learning.entity.ResourceGenerationTask;
import com.learning.service.LearningResourceService;
import com.learning.service.TaskDispatchService;
import com.learning.service.TaskSseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Tag(name = "任务管理")
@RestController
@RequestMapping("/api/task")
@RequiredArgsConstructor
public class TaskController {

    private final TaskDispatchService taskDispatchService;
    private final LearningResourceService resourceService;
    private final TaskSseService taskSseService;

    @Operation(summary = "分派生成任务")
    @PostMapping("/dispatch")
    public Result<ResourceGenerationTask> dispatchTask(@Valid @RequestBody TaskDispatchRequest request) {
        return Result.success(taskDispatchService.dispatchTask(
                request.getPlanId(), request.getResourceId(), request.getAgentChain()));
    }

    @Operation(summary = "查询任务状态")
    @GetMapping("/{taskId}")
    public Result<ResourceGenerationTask> getTask(@PathVariable Long taskId) {
        return Result.success(resourceService.getTaskById(taskId));
    }

    @Operation(summary = "重试任务")
    @PostMapping("/{taskId}/retry")
    public Result<Void> retryTask(@PathVariable Long taskId) {
        taskDispatchService.retryTask(taskId);
        return Result.success();
    }

    @Operation(summary = "SSE 订阅任务状态推送")
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamTasks(@RequestParam Long userId) {
        return taskSseService.subscribe(userId);
    }

    @Operation(summary = "内部接口：创建资源生成任务")
    @PostMapping("/internal/create")
    public Result<ResourceGenerationTask> createTaskInternal(@RequestBody java.util.Map<String, Object> body) {
        Long planId = Long.valueOf(body.get("planId").toString());
        Long resourceId = Long.valueOf(body.get("resourceId").toString());
        String agentChain = body.get("agentChain") != null ? body.get("agentChain").toString() : null;
        return Result.success(taskDispatchService.dispatchTask(planId, resourceId, agentChain));
    }

    @Operation(summary = "内部接口：更新任务状态")
    @PutMapping("/internal/{taskId}")
    public Result<Void> updateTaskInternal(@PathVariable Long taskId,
                                            @RequestBody java.util.Map<String, Object> body) {
        Integer status = body.get("taskStatus") != null ? Integer.valueOf(body.get("taskStatus").toString()) : null;
        if (status != null) {
            taskDispatchService.updateTaskStatus(taskId, status);
        }
        return Result.success();
    }
}
