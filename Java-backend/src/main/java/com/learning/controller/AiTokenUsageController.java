package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.AiTokenUsage;
import com.learning.mapper.AiTokenUsageMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@Tag(name = "AI Token消耗")
@RestController
@RequestMapping("/api/token")
@RequiredArgsConstructor
public class AiTokenUsageController {

    private final AiTokenUsageMapper tokenUsageMapper;

    @Operation(summary = "内部接口：记录Token消耗")
    @PostMapping("/internal/record")
    public Result<AiTokenUsage> recordTokenUsage(@RequestBody Map<String, Object> body) {
        AiTokenUsage usage = new AiTokenUsage();
        usage.setUserId(Long.valueOf(body.get("userId").toString()));
        usage.setScene((String) body.get("scene"));
        usage.setModelName((String) body.get("modelName"));
        usage.setInputTokens(Integer.valueOf(body.get("inputTokens").toString()));
        usage.setOutputTokens(Integer.valueOf(body.get("outputTokens").toString()));
        if (body.get("taskId") != null) {
            usage.setTaskId(Long.valueOf(body.get("taskId").toString()));
        }
        usage.setCreatedAt(LocalDateTime.now());
        tokenUsageMapper.insert(usage);
        return Result.success(usage);
    }
}
