package com.learning.controller;

import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.entity.KnowledgeBase;
import com.learning.service.KnowledgeBaseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Tag(name = "知识库管理")
@RestController
@RequestMapping("/api/admin/kb")
@RequiredArgsConstructor
public class KnowledgeBaseController {

    private final KnowledgeBaseService kbService;

    @Operation(summary = "创建知识库记录（仅元数据，文件由 Python 端处理）")
    @PostMapping("/create")
    public Result<KnowledgeBase> create(Authentication authentication,
                                        @RequestBody Map<String, Object> body) {
        Long userId = (Long) authentication.getPrincipal();
        String docName = (String) body.get("docName");
        Long fileSize = body.get("fileSize") != null ? Long.valueOf(body.get("fileSize").toString()) : 0L;

        KnowledgeBase kb = new KnowledgeBase();
        kb.setDocName(docName);
        kb.setFilePath("/");
        kb.setFileSize(fileSize);
        kb.setUploadUserId(userId);
        kb.setParseStatus(0);

        return Result.success(kbService.createKnowledgeBase(kb));
    }

    @Operation(summary = "获取知识库列表")
    @GetMapping("/list")
    public Result<PageResult<KnowledgeBase>> getList(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        return Result.success(kbService.getList(page, size));
    }

    @Operation(summary = "获取知识库详情")
    @GetMapping("/{id}")
    public Result<KnowledgeBase> getById(@PathVariable Long id) {
        return Result.success(kbService.getById(id));
    }

    @Operation(summary = "删除知识库文档")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        kbService.deleteById(id);
        return Result.success();
    }

    // ==================== 内部 API（供 Python 后端调用） ====================

    @Operation(summary = "内部API - 更新知识库状态")
    @PutMapping("/internal/{id}/status")
    public Result<Void> updateStatusInternal(@PathVariable Long id,
                                              @RequestBody Map<String, Object> body) {
        Integer status = body.get("parseStatus") != null ? Integer.valueOf(body.get("parseStatus").toString()) : null;
        Integer chunkCount = body.get("chunkCount") != null ? Integer.valueOf(body.get("chunkCount").toString()) : null;
        String mineruTaskId = (String) body.get("mineruTaskId");
        String collectionName = (String) body.get("collectionName");
        kbService.updateStatus(id, status, chunkCount, mineruTaskId, collectionName);
        return Result.success();
    }

    @Operation(summary = "内部API - 获取知识库详情")
    @GetMapping("/internal/{id}")
    public Result<KnowledgeBase> getByIdInternal(@PathVariable Long id) {
        return Result.success(kbService.getById(id));
    }

    @Operation(summary = "内部API - 删除知识库")
    @DeleteMapping("/internal/{id}")
    public Result<Void> deleteInternal(@PathVariable Long id) {
        kbService.deleteById(id);
        return Result.success();
    }
}
