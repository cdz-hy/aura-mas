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

    @Operation(summary = "内部接口：软删除对话记录")
    @DeleteMapping("/api/internal/dialogue/{dialogueId}")
    public Result<Void> deleteDialogue(@PathVariable Long dialogueId) {
        dialogueService.deleteDialogue(dialogueId);
        return Result.success();
    }

    @Operation(summary = "内部接口：更新对话记录的资源ID")
    @PutMapping("/api/internal/dialogue/{dialogueId}/resource")
    public Result<Void> updateResourceId(
            @PathVariable Long dialogueId,
            @RequestParam Long resourceId) {
        dialogueService.updateResourceId(dialogueId, resourceId);
        return Result.success();
    }

    @Operation(summary = "内部接口：获取对话历史")
    @GetMapping("/api/internal/dialogue/history")
    public Result<List<AiDialogue>> getHistory(
            @RequestParam Long userId,
            @RequestParam(required = false) Long planId,
            @RequestParam(required = false) String sessionId,
            @RequestParam(required = false) String intentType,
            @RequestParam(defaultValue = "50") int limit) {
        if (sessionId != null && !sessionId.isEmpty()) {
            return Result.success(dialogueService.getHistoryBySession(sessionId, planId, limit));
        }
        return Result.success(dialogueService.getHistory(userId, planId, intentType, limit));
    }

    // ===== User-facing endpoints (JWT authenticated) =====

    @Operation(summary = "获取指定学习计划的所有对话历史")
    @GetMapping("/api/dialogue/history")
    public Result<List<AiDialogue>> getDialogueHistory(
            Authentication authentication,
            @RequestParam Long planId,
            @RequestParam(defaultValue = "200") int limit) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(dialogueService.getHistoryByPlan(userId, planId, limit));
    }

    @Operation(summary = "获取会话列表")
    @GetMapping("/api/dialogue/sessions")
    public Result<List<Map<String, Object>>> getSessions(
            Authentication authentication,
            @RequestParam(required = false) String intentType,
            @RequestParam(required = false) Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(dialogueService.getSessionList(userId, intentType, planId));
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
