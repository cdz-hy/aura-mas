package com.learning.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.Result;
import com.learning.dto.TaskDispatchRequest;
import com.learning.entity.ResourceGenerationTask;
import com.learning.mapper.ResourceGenerationTaskMapper;
import com.learning.service.LearningResourceService;
import com.learning.service.TaskDispatchService;
import com.learning.service.TaskSseService;
import com.fasterxml.jackson.databind.ObjectMapper;
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
    private final ResourceGenerationTaskMapper taskMapper;
    private final ObjectMapper objectMapper;

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

    @Operation(summary = "根据资源ID查询最新任务")
    @GetMapping("/by-resource/{resourceId}")
    public Result<ResourceGenerationTask> getLatestTaskByResource(@PathVariable Long resourceId) {
        ResourceGenerationTask task = taskMapper.selectOne(
                new LambdaQueryWrapper<ResourceGenerationTask>()
                        .eq(ResourceGenerationTask::getResourceId, resourceId)
                        .orderByDesc(ResourceGenerationTask::getId)
                        .last("LIMIT 1"));
        return Result.success(task);
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
        String agentChain = parseAgentChain(body.get("agentChain"));
        return Result.success(taskDispatchService.createInternalTask(planId, resourceId, agentChain));
    }

    @Operation(summary = "内部接口：完成任务（原子性：保存内容 + 更新状态）")
    @PutMapping("/internal/{taskId}/complete")
    public Result<Void> completeTaskInternal(@PathVariable Long taskId,
                                              @RequestBody java.util.Map<String, Object> body) {
        String moduleData = (String) body.get("moduleData");
        taskDispatchService.completeTask(taskId, moduleData);
        return Result.success();
    }

    @Operation(summary = "内部接口：获取所有卡死任务（task_status=1，resource_status=1）")
    @GetMapping("/internal/stuck")
    public Result<java.util.List<ResourceGenerationTask>> getStuckTasks() {
        // 直接用 SQL 关联查询，避免 N+1
        java.util.List<ResourceGenerationTask> stuck = taskMapper.selectList(
                new LambdaQueryWrapper<ResourceGenerationTask>()
                        .eq(ResourceGenerationTask::getTaskStatus, 1)
                        .inSql(ResourceGenerationTask::getResourceId,
                                "SELECT id FROM learning_resource WHERE status = 1")
                        .orderByAsc(ResourceGenerationTask::getId));
        return Result.success(stuck);
    }

    @Operation(summary = "内部接口：更新任务状态")
    @PutMapping("/internal/{taskId}")
    public Result<Void> updateTaskInternal(@PathVariable Long taskId,
                                            @RequestBody java.util.Map<String, Object> body) {
        Integer status = body.get("taskStatus") != null ? Integer.valueOf(body.get("taskStatus").toString()) : null;
        boolean updateResourceStatus = body.get("updateResourceStatus") == null
                || Boolean.parseBoolean(body.get("updateResourceStatus").toString());
        if (status != null) {
            taskDispatchService.updateTaskStatus(taskId, status, updateResourceStatus);
        }
        return Result.success();
    }

    private String parseAgentChain(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof String text) {
            return text;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return value.toString();
        }
    }
}
