package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.entity.*;
import com.learning.mapper.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class StatsService {

    private final LearningPlanMapper planMapper;
    private final LearningResourceMapper resourceMapper;
    private final LearningDurationMapper durationMapper;
    private final NoteMapper noteMapper;
    private final QuizRecordMapper quizRecordMapper;
    private final UserLearningProgressMapper progressMapper;

    public Map<String, Object> getDashboardStats(Long userId) {
        Map<String, Object> stats = new HashMap<>();

        long planCount = planMapper.selectCount(
                new LambdaQueryWrapper<LearningPlan>().eq(LearningPlan::getUserId, userId));
        stats.put("totalPlans", planCount);

        long activePlanCount = planMapper.selectCount(
                new LambdaQueryWrapper<LearningPlan>()
                        .eq(LearningPlan::getUserId, userId)
                        .eq(LearningPlan::getStatus, 3));
        stats.put("activePlans", activePlanCount);

        long completedPlanCount = planMapper.selectCount(
                new LambdaQueryWrapper<LearningPlan>()
                        .eq(LearningPlan::getUserId, userId)
                        .eq(LearningPlan::getStatus, 4));
        stats.put("completedPlans", completedPlanCount);

        long noteCount = noteMapper.selectCount(
                new LambdaQueryWrapper<Note>().eq(Note::getUserId, userId));
        stats.put("totalNotes", noteCount);

        long quizCount = quizRecordMapper.selectCount(
                new LambdaQueryWrapper<QuizRecord>().eq(QuizRecord::getUserId, userId));
        stats.put("totalQuizzes", quizCount);

        long correctQuizCount = quizRecordMapper.selectCount(
                new LambdaQueryWrapper<QuizRecord>()
                        .eq(QuizRecord::getUserId, userId)
                        .eq(QuizRecord::getIsCorrect, 1));
        stats.put("correctQuizzes", correctQuizCount);

        LocalDateTime todayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime todayEnd = LocalDateTime.of(LocalDate.now(), LocalTime.MAX);

        List<LearningDuration> todayDurations = durationMapper.selectList(
                new LambdaQueryWrapper<LearningDuration>()
                        .eq(LearningDuration::getUserId, userId)
                        .between(LearningDuration::getCreatedAt, todayStart, todayEnd));

        int todaySeconds = todayDurations.stream()
                .mapToInt(d -> d.getDurationSeconds() != null ? d.getDurationSeconds() : 0)
                .sum();
        stats.put("todayDurationSeconds", todaySeconds);

        List<LearningDuration> allDurations = durationMapper.selectList(
                new LambdaQueryWrapper<LearningDuration>()
                        .eq(LearningDuration::getUserId, userId));

        int totalSeconds = allDurations.stream()
                .mapToInt(d -> d.getDurationSeconds() != null ? d.getDurationSeconds() : 0)
                .sum();
        stats.put("totalDurationSeconds", totalSeconds);

        long completedResources = progressMapper.selectCount(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .eq(UserLearningProgress::getStatus, 2));
        stats.put("completedResources", completedResources);

        return stats;
    }
}
