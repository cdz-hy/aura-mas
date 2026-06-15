package com.learning.controller;

import com.learning.common.Result;
import com.learning.service.UserLearningProgressService;
import com.learning.util.AuthUtils;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@Tag(name = "学习时长")
@RestController
@RequestMapping("/api/progress")
@RequiredArgsConstructor
public class DurationController {

    private final UserLearningProgressService progressService;

    @Operation(summary = "学习心跳上报")
    @PostMapping("/heartbeat")
    public Result<Void> heartbeat(
            Authentication authentication,
            @RequestParam Long planId,
            @RequestParam Long resourceId,
            @RequestParam int elapsedSeconds) {
        Long userId = AuthUtils.getCurrentUserId(authentication);
        progressService.heartbeat(userId, planId, resourceId, elapsedSeconds);
        return Result.success(null);
    }
}
