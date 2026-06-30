package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.dto.NoteCreateRequest;
import com.learning.entity.Note;
import com.learning.entity.NoteResourceRel;
import com.learning.service.NoteService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "笔记管理")
@RestController
@RequestMapping("/api/note")
@RequiredArgsConstructor
public class NoteController {

    private final NoteService noteService;

    @Operation(summary = "创建笔记")
    @OperationLog(type = OperationType.NOTE_CREATE, module = "Note",
            desc = "'创建笔记: ' + #request.getNoteName()",
            resourceId = "#result?.data?.id?.toString()")
    @PostMapping
    public Result<Note> createNote(Authentication authentication,
                                    @Valid @RequestBody NoteCreateRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(noteService.createNote(userId, request));
    }

    @Operation(summary = "获取笔记详情")
    @GetMapping("/{noteId}")
    public Result<Note> getNote(Authentication authentication,
                                 @PathVariable Long noteId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(noteService.getNoteById(noteId, userId));
    }

    @Operation(summary = "获取用户笔记列表")
    @GetMapping("/list")
    public Result<PageResult<Note>> getNotes(Authentication authentication,
                                              @RequestParam(defaultValue = "1") int page,
                                              @RequestParam(defaultValue = "10") int size,
                                              @RequestParam(required = false) String keyword) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(noteService.getUserNotes(userId, page, size, keyword));
    }

    @Operation(summary = "更新笔记")
    @OperationLog(type = OperationType.NOTE_UPDATE, module = "Note",
            desc = "'更新笔记ID: ' + #noteId",
            resourceId = "#noteId?.toString()")
    @PutMapping("/{noteId}")
    public Result<Note> updateNote(Authentication authentication,
                                    @PathVariable Long noteId,
                                    @Valid @RequestBody NoteCreateRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(noteService.updateNote(noteId, userId, request));
    }

    @Operation(summary = "删除笔记")
    @OperationLog(type = OperationType.NOTE_DELETE, module = "Note",
            desc = "'删除笔记ID: ' + #noteId",
            resourceId = "#noteId?.toString()")
    @DeleteMapping("/{noteId}")
    public Result<Void> deleteNote(Authentication authentication,
                                    @PathVariable Long noteId) {
        Long userId = (Long) authentication.getPrincipal();
        noteService.deleteNote(noteId, userId);
        return Result.success();
    }

    @Operation(summary = "关联笔记与资源")
    @PostMapping("/{noteId}/link-resource")
    public Result<Void> linkResource(Authentication authentication,
                                      @PathVariable Long noteId,
                                      @RequestBody Map<String, Object> body) {
        Long userId = (Long) authentication.getPrincipal();
        noteService.getNoteById(noteId, userId); // 校验笔记所有权
        Object resourceObj = body.get("resourceId");
        if (resourceObj == null) {
            return Result.error(400, "resourceId 不能为空");
        }
        Long resourceId = Long.valueOf(resourceObj.toString());
        String selectedText = body.get("selectedText") != null ? body.get("selectedText").toString() : null;
        String positionInfo = body.get("positionInfo") != null ? body.get("positionInfo").toString() : null;
        Object planObj = body.get("planId");
        Long planId = planObj != null ? Long.valueOf(planObj.toString()) : null;
        String moduleName = body.get("moduleName") != null ? body.get("moduleName").toString() : null;
        String resourceTitle = body.get("resourceTitle") != null ? body.get("resourceTitle").toString() : null;
        noteService.linkResource(noteId, resourceId, selectedText, positionInfo, planId, moduleName, resourceTitle);
        return Result.success();
    }

    @Operation(summary = "取消笔记与资源关联")
    @DeleteMapping("/unlink-resource")
    public Result<Void> unlinkResource(@RequestBody Map<String, Long> body) {
        noteService.unlinkResource(body.get("noteId"), body.get("resourceId"));
        return Result.success();
    }

    @Operation(summary = "获取笔记关联的资源")
    @GetMapping("/{noteId}/resources")
    public Result<List<NoteResourceRel>> getNoteResources(@PathVariable Long noteId) {
        return Result.success(noteService.getNoteResourceRels(noteId));
    }

    @Operation(summary = "内部接口：获取笔记内容")
    @GetMapping("/internal/{noteId}")
    public Result<Note> getNoteInternal(@PathVariable Long noteId) {
        return Result.success(noteService.getNoteById(noteId));
    }
}
