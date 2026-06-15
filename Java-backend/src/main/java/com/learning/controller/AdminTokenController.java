package com.learning.controller;

import com.learning.common.Result;
import com.learning.service.AiTokenUsageService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Tag(name = "管理员-Token消耗分析")
@RestController
@RequestMapping("/api/admin/token")
@RequiredArgsConstructor
public class AdminTokenController {

    private final AiTokenUsageService aiTokenUsageService;

    @Operation(summary = "获取Token消耗分析数据")
    @GetMapping("/analysis")
    public Result<Map<String, Object>> getAnalysis(
            @RequestParam String start,
            @RequestParam String end) {
        return Result.success(aiTokenUsageService.getFullAnalysis(start, end));
    }

    @Operation(summary = "分页查询Token消耗记录")
    @GetMapping("/records")
    public Result<Map<String, Object>> getRecords(
            @RequestParam String start,
            @RequestParam String end,
            @RequestParam(required = false) String model,
            @RequestParam(required = false) String scene,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return Result.success(aiTokenUsageService.getRecords(start, end, model, scene, page, size));
    }
}
