package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.Result;
import com.learning.service.FileService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;

@Tag(name = "文件管理")
@RestController
@RequestMapping("/api/file")
@RequiredArgsConstructor
public class FileController {

    private final FileService fileService;

    @Operation(summary = "通用文件上传")
    @OperationLog(type = OperationType.FILE_UPLOAD, module = "File", desc = "文件上传")
    @PostMapping("/upload")
    public Result<Map<String, String>> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(defaultValue = "general") String directory) {

        String path = fileService.uploadFile(file, directory);

        Map<String, String> result = new HashMap<>();
        result.put("path", path);
        result.put("url", fileService.getPresignedUrl(path));
        return Result.success(result);
    }

    @Operation(summary = "获取文件下载链接")
    @GetMapping("/url")
    public Result<String> getFileUrl(@RequestParam String path) {
        return Result.success(fileService.getPresignedUrl(path));
    }
}
