package com.learning.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.common.Result;
import com.learning.entity.LearningResource;
import com.learning.entity.QuizRecord;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.QuizRecordMapper;
import com.learning.service.UserLearningProgressService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Slf4j
@Tag(name = "答题记录")
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class QuizRecordController {

    private final QuizRecordMapper quizRecordMapper;
    private final LearningResourceMapper resourceMapper;
    private final UserLearningProgressService progressService;
    private final ObjectMapper objectMapper;

    @Operation(summary = "内部接口：创建答题记录")
    @PostMapping("/quiz/internal/create")
    public Result<QuizRecord> createQuizRecord(@RequestBody Map<String, Object> body) {
        try {
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

            // 检查是否所有题目都已答完，自动标记完成
            try {
                Long resourceId = record.getResourceId();
                Long userId = record.getUserId();
                Long planId = record.getPlanId();

                Long answeredCount = quizRecordMapper.selectCount(
                        new LambdaQueryWrapper<QuizRecord>()
                                .eq(QuizRecord::getUserId, userId)
                                .eq(QuizRecord::getResourceId, resourceId));

                LearningResource resource = resourceMapper.selectById(resourceId);
                if (resource != null && resource.getModuleData() != null) {
                    JsonNode moduleData = objectMapper.readTree(resource.getModuleData());
                    int totalQuestions = moduleData.has("total_questions")
                            ? moduleData.get("total_questions").asInt()
                            : (moduleData.has("questions") ? moduleData.get("questions").size() : 0);

                    if (totalQuestions > 0 && answeredCount >= totalQuestions) {
                        progressService.markComplete(userId, planId, resourceId);
                        log.info("测验资源 {} 已全部答完，自动标记完成", resourceId);
                    }
                }
            } catch (Exception e) {
                log.warn("测验自动完成检测失败: {}", e.getMessage());
            }

            return Result.success(record);
        } catch (Exception e) {
            log.error("创建答题记录失败: {}", e.getMessage(), e);
            throw e;
        }
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
