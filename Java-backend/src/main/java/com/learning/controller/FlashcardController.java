package com.learning.controller;

import com.learning.common.ErrorCode;
import com.learning.common.Result;
import com.learning.entity.Flashcard;
import com.learning.service.FlashcardService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "闪卡管理")
@RestController
@RequestMapping("/api/flashcard")
@RequiredArgsConstructor
public class FlashcardController {

    private final FlashcardService flashcardService;

    @Operation(summary = "获取笔记的所有闪卡")
    @GetMapping("/by-note/{noteId}")
    public Result<List<Flashcard>> getByNote(Authentication auth,
                                              @PathVariable Long noteId) {
        Long userId = (Long) auth.getPrincipal();
        return Result.success(flashcardService.getByNoteId(noteId, userId));
    }

    @Operation(summary = "获取待复习的闪卡")
    @GetMapping("/review")
    public Result<List<Flashcard>> getDueCards(Authentication auth,
                                                @RequestParam(defaultValue = "10") int limit) {
        Long userId = (Long) auth.getPrincipal();
        return Result.success(flashcardService.getDueCards(userId, limit));
    }

    @Operation(summary = "获取待复习闪卡数量")
    @GetMapping("/review/count")
    public Result<Long> getDueCount(Authentication auth) {
        Long userId = (Long) auth.getPrincipal();
        return Result.success(flashcardService.countDueCards(userId));
    }

    @Operation(summary = "提交复习结果")
    @PutMapping("/{cardId}/review")
    public Result<Flashcard> reviewCard(Authentication auth,
                                         @PathVariable Long cardId,
                                         @RequestBody Map<String, Integer> body) {
        Long userId = (Long) auth.getPrincipal();
        int quality = body.get("quality");
        if (quality < 1 || quality > 5) {
            return Result.error(ErrorCode.BAD_REQUEST.getCode(), "quality 必须在 1-5 之间");
        }
        return Result.success(flashcardService.reviewCard(cardId, userId, quality));
    }

    @Operation(summary = "保存闪卡（AI 生成后调用）")
    @PostMapping("/save")
    public Result<Void> saveFlashcards(Authentication auth,
                                        @RequestBody Map<String, Object> body) {
        Long userId = (Long) auth.getPrincipal();
        Long noteId = Long.valueOf(body.get("noteId").toString());
        List<Flashcard> cards = parseCards(body);
        flashcardService.saveFlashcards(noteId, userId, cards);
        return Result.success();
    }

    @Operation(summary = "内部接口：保存闪卡")
    @PostMapping("/internal/save")
    public Result<Void> saveFlashcardsInternal(@RequestBody Map<String, Object> body) {
        Long userId = Long.valueOf(body.get("userId").toString());
        Long noteId = Long.valueOf(body.get("noteId").toString());
        List<Flashcard> cards = parseCards(body);
        flashcardService.saveFlashcards(noteId, userId, cards);
        return Result.success();
    }

    @Operation(summary = "内部接口：删除笔记的所有闪卡")
    @DeleteMapping("/internal/by-note/{noteId}")
    public Result<Void> deleteByNote(@PathVariable Long noteId,
                                      @RequestParam Long userId) {
        flashcardService.deleteByNoteId(noteId, userId);
        return Result.success();
    }

    private List<Flashcard> parseCards(Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cardsData = (List<Map<String, Object>>) body.get("cards");
        List<Flashcard> cards = new java.util.ArrayList<>();
        for (Map<String, Object> c : cardsData) {
            Flashcard fc = new Flashcard();
            fc.setQuestion((String) c.get("question"));
            fc.setAnswer((String) c.get("answer"));
            fc.setDifficulty(c.get("difficulty") != null ? Integer.valueOf(c.get("difficulty").toString()) : 1);
            cards.add(fc);
        }
        return cards;
    }

    @Operation(summary = "删除闪卡")
    @DeleteMapping("/{cardId}")
    public Result<Void> deleteCard(Authentication auth,
                                    @PathVariable Long cardId) {
        Long userId = (Long) auth.getPrincipal();
        flashcardService.deleteCard(cardId, userId);
        return Result.success();
    }
}
