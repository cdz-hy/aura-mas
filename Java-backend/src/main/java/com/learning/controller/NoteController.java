package com.learning.controller;

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
                                              @RequestParam(defaultValue = "10") int size) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(noteService.getUserNotes(userId, page, size));
    }

    @Operation(summary = "更新笔记")
    @PutMapping("/{noteId}")
    public Result<Note> updateNote(Authentication authentication,
                                    @PathVariable Long noteId,
                                    @Valid @RequestBody NoteCreateRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(noteService.updateNote(noteId, userId, request));
    }

    @Operation(summary = "删除笔记")
    @DeleteMapping("/{noteId}")
    public Result<Void> deleteNote(Authentication authentication,
                                    @PathVariable Long noteId) {
        Long userId = (Long) authentication.getPrincipal();
        noteService.deleteNote(noteId, userId);
        return Result.success();
    }

    @Operation(summary = "关联笔记与资源")
    @PostMapping("/link-resource")
    public Result<Void> linkResource(@RequestBody Map<String, Long> body) {
        noteService.linkResource(body.get("noteId"), body.get("resourceId"));
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
}
