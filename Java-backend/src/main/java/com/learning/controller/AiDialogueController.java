package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.AiDialogue;
import com.learning.service.AiDialogueService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "AI对话记录")
@RestController
@RequiredArgsConstructor
public class AiDialogueController {

    private final AiDialogueService dialogueService;

    // ===== Internal endpoints (service-to-service) =====

    @Operation(summary = "内部接口：创建对话记录")
    @PostMapping("/api/internal/dialogue")
    public Result<AiDialogue> create(@RequestBody Map<String, Object> body) {
        Long userId = Long.valueOf(body.get("userId").toString());
        String sessionId = (String) body.get("sessionId");
        Long planId = body.get("planId") != null ? Long.valueOf(body.get("planId").toString()) : null;
        String conversationText = (String) body.get("conversationText");
        String dialogueType = (String) body.get("dialogueType");
        String intentType = (String) body.get("intentType");
        return Result.success(dialogueService.createDialogue(userId, sessionId, planId, conversationText, dialogueType, intentType));
    }

    @Operation(summary = "内部接口：获取对话历史")
    @GetMapping("/api/internal/dialogue/history")
    public Result<List<AiDialogue>> getHistory(
            @RequestParam Long userId,
            @RequestParam(required = false) Long planId,
            @RequestParam(required = false) String intentType,
            @RequestParam(defaultValue = "50") int limit) {
        return Result.success(dialogueService.getHistory(userId, planId, intentType, limit));
    }

    // ===== User-facing endpoints (JWT authenticated) =====

    @Operation(summary = "获取会话列表")
    @GetMapping("/api/dialogue/sessions")
    public Result<List<Map<String, Object>>> getSessions(
            Authentication authentication,
            @RequestParam(required = false) String intentType) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(dialogueService.getSessionList(userId, intentType));
    }

    @Operation(summary = "获取会话消息历史")
    @GetMapping("/api/dialogue/session/{sessionId}")
    public Result<List<AiDialogue>> getSessionMessages(
            @PathVariable String sessionId,
            @RequestParam(defaultValue = "100") int limit) {
        return Result.success(dialogueService.getHistoryBySession(sessionId, limit));
    }

    @Operation(summary = "删除会话")
    @DeleteMapping("/api/dialogue/session/{sessionId}")
    public Result<Void> deleteSession(@PathVariable String sessionId) {
        dialogueService.deleteBySession(sessionId);
        return Result.success();
    }

    @Operation(summary = "将会话关联到学习计划")
    @PutMapping("/api/dialogue/session/{sessionId}/link-plan/{planId}")
    public Result<Void> linkSessionToPlan(@PathVariable String sessionId, @PathVariable Long planId) {
        dialogueService.linkSessionToPlan(sessionId, planId);
        return Result.success();
    }
}
