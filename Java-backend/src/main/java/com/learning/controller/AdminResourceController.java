package com.learning.controller;

import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.entity.ResourceLibrary;
import com.learning.service.AdminResourceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@Tag(name = "管理员-资源库管理")
@RestController
@RequestMapping("/api/admin/resource")
@RequiredArgsConstructor
public class AdminResourceController {

    private final AdminResourceService adminResourceService;

    @Operation(summary = "分页查询资源库列表")
    @GetMapping
    public Result<PageResult<ResourceLibrary>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String contentType,
            @RequestParam(required = false) Integer status) {
        return Result.success(adminResourceService.list(page, size, keyword, contentType, status));
    }

    @Operation(summary = "获取资源详情")
    @GetMapping("/{id}")
    public Result<ResourceLibrary> getById(@PathVariable Long id) {
        return Result.success(adminResourceService.getById(id));
    }

    @Operation(summary = "保存草稿（AI 生成后暂存）")
    @PostMapping("/save-draft")
    public Result<ResourceLibrary> saveDraft(Authentication authentication,
                                              @RequestBody ResourceLibrary resource) {
        Long userId = (Long) authentication.getPrincipal();
        resource.setCreatedBy(userId);
        return Result.success(adminResourceService.saveDraft(resource));
    }

    @Operation(summary = "审核通过并入库")
    @PutMapping("/{id}/approve")
    public Result<ResourceLibrary> approve(@PathVariable Long id) {
        return Result.success(adminResourceService.approve(id));
    }

    @Operation(summary = "拒绝")
    @PutMapping("/{id}/reject")
    public Result<ResourceLibrary> reject(@PathVariable Long id) {
        return Result.success(adminResourceService.reject(id));
    }

    @Operation(summary = "更新资源内容（改写后保存）")
    @PutMapping("/{id}")
    public Result<ResourceLibrary> update(@PathVariable Long id,
                                           @RequestBody ResourceLibrary resource) {
        return Result.success(adminResourceService.update(id, resource));
    }

    @Operation(summary = "删除资源")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        adminResourceService.delete(id);
        return Result.success();
    }
}
