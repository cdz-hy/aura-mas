package com.learning.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.Result;
import com.learning.entity.QuizRecord;
import com.learning.mapper.QuizRecordMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Tag(name = "答题记录")
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class QuizRecordController {

    private final QuizRecordMapper quizRecordMapper;

    @Operation(summary = "内部接口：创建答题记录")
    @PostMapping("/quiz/internal/create")
    public Result<QuizRecord> createQuizRecord(@RequestBody Map<String, Object> body) {
        QuizRecord record = new QuizRecord();
        record.setResourceId(Long.valueOf(body.get("resourceId").toString()));
        record.setUserId(Long.valueOf(body.get("userId").toString()));
        record.setPlanId(Long.valueOf(body.get("planId").toString()));
        record.setQuestionType((String) body.get("questionType"));
        record.setQuestionText((String) body.get("questionText"));
        record.setCorrectAnswer((String) body.get("correctAnswer"));
        record.setUserAnswer((String) body.get("userAnswer"));
        record.setScore(body.get("score") != null ? Double.valueOf(body.get("score").toString()) : null);
        record.setIsCorrect(Integer.valueOf(body.get("isCorrect").toString()));
        record.setFeedback((String) body.get("feedback"));
        record.setDifficulty(body.get("difficulty") != null ? Integer.valueOf(body.get("difficulty").toString()) : 3);
        record.setAnswerTime(LocalDateTime.now());
        quizRecordMapper.insert(record);
        return Result.success(record);
    }

    @Operation(summary = "内部接口：获取用户答题记录")
    @GetMapping("/quiz/internal/user/{userId}")
    public Result<List<QuizRecord>> getUserQuizRecords(
            @PathVariable Long userId,
            @RequestParam(required = false) Long planId,
            @RequestParam(required = false) Long resourceId,
            @RequestParam(defaultValue = "50") int limit) {
        LambdaQueryWrapper<QuizRecord> wrapper = new LambdaQueryWrapper<QuizRecord>()
                .eq(QuizRecord::getUserId, userId)
                .eq(planId != null, QuizRecord::getPlanId, planId)
                .eq(resourceId != null, QuizRecord::getResourceId, resourceId)
                .orderByDesc(QuizRecord::getAnswerTime)
                .last("LIMIT " + limit);
        return Result.success(quizRecordMapper.selectList(wrapper));
    }

    @Operation(summary = "内部接口：获取计划答题统计")
    @GetMapping("/quiz/internal/stats/{planId}")
    public Result<Map<String, Object>> getQuizStats(
            @PathVariable Long planId,
            @RequestParam Long userId) {
        LambdaQueryWrapper<QuizRecord> wrapper = new LambdaQueryWrapper<QuizRecord>()
                .eq(QuizRecord::getUserId, userId)
                .eq(QuizRecord::getPlanId, planId);
        List<QuizRecord> records = quizRecordMapper.selectList(wrapper);

        long total = records.size();
        long correct = records.stream().filter(r -> r.getIsCorrect() != null && r.getIsCorrect() == 1).count();
        double accuracy = total > 0 ? (double) correct / total : 0;
        double avgScore = records.stream()
                .filter(r -> r.getScore() != null)
                .mapToDouble(QuizRecord::getScore)
                .average().orElse(0);

        return Result.success(Map.of(
                "totalQuestions", total,
                "correctAnswers", correct,
                "accuracy", accuracy,
                "avgScore", Math.round(avgScore * 1000) / 10.0
        ));
    }
}
