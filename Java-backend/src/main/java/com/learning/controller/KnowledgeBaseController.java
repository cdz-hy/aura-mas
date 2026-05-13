package com.learning.controller;

import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.entity.KnowledgeBase;
import com.learning.service.FileService;
import com.learning.service.KnowledgeBaseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Tag(name = "知识库管理")
@RestController
@RequestMapping("/api/admin/kb")
@RequiredArgsConstructor
public class KnowledgeBaseController {

    private final KnowledgeBaseService kbService;
    private final FileService fileService;

    @Operation(summary = "上传知识库文档")
    @PostMapping("/upload")
    public Result<KnowledgeBase> upload(Authentication authentication,
                                         @RequestParam("file") MultipartFile file,
                                         @RequestParam("docName") String docName) {
        Long userId = (Long) authentication.getPrincipal();

        String filePath = fileService.uploadFile(file, "knowledge-base");

        KnowledgeBase kb = new KnowledgeBase();
        kb.setDocName(docName);
        kb.setFilePath(filePath);
        kb.setFileSize(file.getSize());
        kb.setUploadUserId(userId);

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
        KnowledgeBase kb = kbService.getById(id);
        if (kb != null) {
            fileService.deleteFile(kb.getFilePath());
        }
        kbService.deleteById(id);
        return Result.success();
    }

    @Operation(summary = "获取下载链接")
    @GetMapping("/{id}/download")
    public Result<String> getDownloadUrl(@PathVariable Long id) {
        KnowledgeBase kb = kbService.getById(id);
        if (kb == null) {
            return Result.error("文档不存在");
        }
        return Result.success(fileService.getPresignedUrl(kb.getFilePath()));
    }
}
