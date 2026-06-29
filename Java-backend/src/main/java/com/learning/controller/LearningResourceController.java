package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.LearningResource;
import com.learning.entity.ResourceGenerationTask;
import com.learning.service.LearningResourceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;

@Tag(name = "学习资源管理")
@RestController
@RequestMapping("/api/resource")
@RequiredArgsConstructor
public class LearningResourceController {

    private final LearningResourceService resourceService;

    @Operation(summary = "获取计划下的资源列表")
    @GetMapping("/plan/{planId}")
    public Result<List<LearningResource>> getResourcesByPlan(@PathVariable Long planId) {
        return Result.success(resourceService.getResourcesByPlanId(planId));
    }

    @Operation(summary = "获取资源详情")
    @GetMapping("/{resourceId}")
    public Result<LearningResource> getResource(@PathVariable Long resourceId) {
        return Result.success(resourceService.getResourceById(resourceId));
    }

    @Operation(summary = "创建学习资源")
    @PostMapping
    public Result<LearningResource> createResource(@RequestBody LearningResource resource) {
        return Result.success(resourceService.createResource(resource));
    }

    @Operation(summary = "删除学习资源")
    @DeleteMapping("/{resourceId}")
    public Result<Void> deleteResource(Authentication authentication,
                                         @PathVariable Long resourceId) {
        Long userId = (Long) authentication.getPrincipal();
        resourceService.deleteResource(resourceId, userId);
        return Result.success();
    }

    @Operation(summary = "更新资源内容(前端调用)")
    @PutMapping("/{resourceId}/content")
    public Result<Void> updateResourceContent(@PathVariable Long resourceId,
                                               @RequestBody java.util.Map<String, Object> body) throws Exception {
        String moduleData = null;
        if (body.get("moduleData") != null) {
            Object raw = body.get("moduleData");
            if (raw instanceof String) {
                // 已经是 JSON 字符串（如 Python 后端调用），直接使用
                moduleData = (String) raw;
            } else {
                // 前端传入的是对象，需要序列化为 JSON 字符串
                ObjectMapper mapper = new ObjectMapper();
                moduleData = mapper.writeValueAsString(raw);
            }
        }
        Integer status = body.get("status") != null ? Integer.valueOf(body.get("status").toString()) : null;
        resourceService.updateContent(resourceId, moduleData, null, status);
        return Result.success();
    }

    @Operation(summary = "批量创建资源(前端调用)")
    @PostMapping("/bulk")
    public Result<List<LearningResource>> bulkCreateUser(@RequestBody List<LearningResource> resources) {
        return Result.success(resourceService.bulkCreate(resources));
    }

    @Operation(summary = "内部接口：批量创建资源")
    @PostMapping("/internal/bulk")
    public Result<List<LearningResource>> bulkCreate(@RequestBody List<LearningResource> resources) {
        return Result.success(resourceService.bulkCreate(resources));
    }

    @Operation(summary = "内部接口：更新资源内容")
    @PutMapping("/internal/{resourceId}/content")
    public Result<Void> updateContent(@PathVariable Long resourceId,
                                       @RequestBody java.util.Map<String, Object> body) {
        String moduleData = (String) body.get("moduleData");
        String moduleType = (String) body.get("moduleType");
        Integer status = body.get("status") != null ? Integer.valueOf(body.get("status").toString()) : null;
        resourceService.updateContent(resourceId, moduleData, moduleType, status);
        return Result.success();
    }

    @Operation(summary = "内部接口：按模块获取资源")
    @GetMapping("/internal/plan/{planId}/module/{moduleOrder}")
    public Result<List<LearningResource>> getResourcesByModule(
            @PathVariable Long planId,
            @PathVariable Integer moduleOrder) {
        return Result.success(resourceService.getResourcesByModule(planId, moduleOrder));
    }

    @Operation(summary = "内部接口：创建单个学习资源")
    @PostMapping("/internal")
    public Result<LearningResource> createResourceInternal(@RequestBody LearningResource resource) {
        return Result.success(resourceService.createResource(resource));
    }

    @Operation(summary = "内部接口：获取计划下的资源列表")
    @GetMapping("/internal/plan/{planId}")
    public Result<List<LearningResource>> getResourcesByPlanInternal(@PathVariable Long planId) {
        return Result.success(resourceService.getResourcesByPlanId(planId));
    }

    @Operation(summary = "内部接口：获取资源详情")
    @GetMapping("/internal/{resourceId}")
    public Result<LearningResource> getResourceInternal(@PathVariable Long resourceId) {
        return Result.success(resourceService.getResourceById(resourceId));
    }

    @Operation(summary = "内部接口：更新资源状态")
    @PutMapping("/internal/{resourceId}/status")
    public Result<Void> updateResourceStatusInternal(@PathVariable Long resourceId,
                                                      @RequestParam Integer status) {
        resourceService.updateResourceStatus(resourceId, status);
        return Result.success();
    }
}
