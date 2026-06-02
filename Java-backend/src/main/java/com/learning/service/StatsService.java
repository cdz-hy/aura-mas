package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.entity.*;
import com.learning.mapper.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class StatsService {

    private final LearningPlanMapper planMapper;
    private final LearningResourceMapper resourceMapper;
    private final LearningDurationMapper durationMapper;
    private final NoteMapper noteMapper;
    private final QuizRecordMapper quizRecordMapper;
    private final UserLearningProgressMapper progressMapper;
    private final DailyStudyTimeMapper dailyStudyTimeMapper;

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

        // 用户所有学习计划对应的学习资源总数
        List<Long> planIds = planMapper.selectList(
                new LambdaQueryWrapper<LearningPlan>()
                        .select(LearningPlan::getId)
                        .eq(LearningPlan::getUserId, userId))
                .stream()
                .map(LearningPlan::getId)
                .collect(Collectors.toList());

        long totalResources = 0;
        if (!planIds.isEmpty()) {
            totalResources = resourceMapper.selectCount(
                    new LambdaQueryWrapper<LearningResource>()
                            .in(LearningResource::getPlanId, planIds));
        }
        stats.put("totalResources", totalResources);

        // 学习时长（从 daily_study_time 累计）
        try {
            List<DailyStudyTime> allDaily = dailyStudyTimeMapper.selectList(
                    new LambdaQueryWrapper<DailyStudyTime>()
                            .eq(DailyStudyTime::getUserId, userId));
            int dailyTotalSeconds = allDaily.stream()
                    .mapToInt(d -> d.getDurationSeconds() != null ? d.getDurationSeconds() : 0)
                    .sum();
            double totalStudyHours = dailyTotalSeconds / 3600.0;
            stats.put("totalStudyHours", Math.round(totalStudyHours * 10) / 10.0);
        } catch (Exception e) {
            log.error("获取学习时长失败", e);
            stats.put("totalStudyHours", 0.0);
        }

        // 答题正确率
        double quizAccuracy = quizCount > 0
                ? Math.round((double) correctQuizCount / quizCount * 1000) / 10.0
                : 0;
        stats.put("quizAccuracy", quizAccuracy);

        // 本周每天学习分钟数
        List<Map<String, Object>> weeklyMinutes = new ArrayList<>();
        try {
            LocalDate today = LocalDate.now();
            LocalDate weekStart = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));

            List<DailyStudyTime> weekDaily = dailyStudyTimeMapper.selectList(
                    new LambdaQueryWrapper<DailyStudyTime>()
                            .eq(DailyStudyTime::getUserId, userId)
                            .ge(DailyStudyTime::getStudyDate, weekStart));

            Map<LocalDate, Integer> dailyMap = new HashMap<>();
            for (DailyStudyTime d : weekDaily) {
                dailyMap.put(d.getStudyDate(), d.getDurationSeconds());
            }

            int[] dailySeconds = new int[7];
            for (int i = 0; i < 7; i++) {
                LocalDate date = weekStart.plusDays(i);
                dailySeconds[i] = dailyMap.getOrDefault(date, 0);
            }

            String[] dayLabels = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
            for (int i = 0; i < 7; i++) {
                Map<String, Object> day = new HashMap<>();
                day.put("label", dayLabels[i]);
                day.put("minutes", dailySeconds[i] / 60);
                weeklyMinutes.add(day);
            }
        } catch (Exception e) {
            log.error("获取本周学习数据失败", e);
            String[] dayLabels = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
            for (String label : dayLabels) {
                Map<String, Object> day = new HashMap<>();
                day.put("label", label);
                day.put("minutes", 0);
                weeklyMinutes.add(day);
            }
        }
        stats.put("weeklyMinutes", weeklyMinutes);

        // 最近活动
        List<Map<String, Object>> recentActivity = new ArrayList<>();
        try {
            LocalDateTime thirtyDaysAgo = LocalDateTime.now().minusDays(30);

            // 收集所有活动，带原始时间戳用于排序
            List<Map<String, Object>> allActivities = new ArrayList<>();

            // 创建学习计划（最近 30 天）
            List<LearningPlan> recentPlans = planMapper.selectList(
                    new LambdaQueryWrapper<LearningPlan>()
                            .eq(LearningPlan::getUserId, userId)
                            .ge(LearningPlan::getCreatedAt, thirtyDaysAgo)
                            .orderByDesc(LearningPlan::getCreatedAt)
                            .last("LIMIT 3"));
            for (LearningPlan plan : recentPlans) {
                Map<String, Object> act = new HashMap<>();
                act.put("text", "创建了学习计划「" + plan.getTitle() + "」");
                act.put("time", _formatTimeAgo(plan.getCreatedAt()));
                act.put("ts", plan.getCreatedAt().atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli());
                act.put("color", "bg-blue-400");
                allActivities.add(act);
            }

            // 最近访问过的资源（有学习记录的）
            List<UserLearningProgress> recentProgress = progressMapper.selectList(
                    new LambdaQueryWrapper<UserLearningProgress>()
                            .eq(UserLearningProgress::getUserId, userId)
                            .isNotNull(UserLearningProgress::getLastAccessTime)
                            .orderByDesc(UserLearningProgress::getLastAccessTime)
                            .last("LIMIT 3"));
            for (UserLearningProgress p : recentProgress) {
                String title = _getResourceTitle(p.getResourceId());
                Map<String, Object> act = new HashMap<>();
                if (p.getStatus() != null && p.getStatus() == 2) {
                    act.put("text", "完成了「" + title + "」模块学习");
                    act.put("color", "bg-emerald-400");
                } else {
                    act.put("text", "正在学习「" + title + "」");
                    act.put("color", "bg-blue-400");
                }
                act.put("time", _formatTimeAgo(p.getLastAccessTime()));
                act.put("ts", p.getLastAccessTime().atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli());
                allActivities.add(act);
            }

            // 完成测验（最近 30 天，只选需要的列避免缺少列的问题）
            List<QuizRecord> recentQuizzes = quizRecordMapper.selectList(
                    new LambdaQueryWrapper<QuizRecord>()
                            .select(QuizRecord::getId, QuizRecord::getResourceId, QuizRecord::getAnswerTime)
                            .eq(QuizRecord::getUserId, userId)
                            .ge(QuizRecord::getAnswerTime, thirtyDaysAgo)
                            .orderByDesc(QuizRecord::getAnswerTime)
                            .last("LIMIT 3"));
            Set<Long> seenResources = new HashSet<>();
            for (QuizRecord q : recentQuizzes) {
                if (seenResources.contains(q.getResourceId())) continue;
                seenResources.add(q.getResourceId());
                String title = _getResourceTitle(q.getResourceId());
                Map<String, Object> act = new HashMap<>();
                act.put("text", "完成了「" + title + "」测验");
                act.put("time", _formatTimeAgo(q.getAnswerTime()));
                act.put("ts", q.getAnswerTime().atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli());
                act.put("color", "bg-amber-400");
                allActivities.add(act);
            }

            // 按时间戳倒序排列（最近的在前面），取前 5 条
            allActivities.sort((a, b) -> Long.compare((long) b.get("ts"), (long) a.get("ts")));
            for (int i = 0; i < Math.min(5, allActivities.size()); i++) {
                Map<String, Object> act = allActivities.get(i);
                act.remove("ts");
                recentActivity.add(act);
            }
        } catch (Exception e) {
            log.error("获取最近活动失败", e);
        }
        stats.put("recentActivity", recentActivity);

        return stats;
    }

    private String _getResourceTitle(Long resourceId) {
        if (resourceId == null) return "未知资源";
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource == null) return "未知资源";
        String moduleData = resource.getModuleData();
        if (moduleData != null && moduleData.contains("\"title\"")) {
            int start = moduleData.indexOf("\"title\"");
            if (start >= 0) {
                int colon = moduleData.indexOf(":", start);
                int quoteStart = moduleData.indexOf("\"", colon + 1);
                int quoteEnd = moduleData.indexOf("\"", quoteStart + 1);
                if (quoteStart >= 0 && quoteEnd > quoteStart) {
                    return moduleData.substring(quoteStart + 1, quoteEnd);
                }
            }
        }
        return resource.getModuleType() != null ? resource.getModuleType() : "未知资源";
    }

    private String _formatTimeAgo(LocalDateTime time) {
        if (time == null) return "";
        LocalDateTime now = LocalDateTime.now();
        long seconds = java.time.Duration.between(time, now).getSeconds();
        if (seconds < 60) return "刚刚";
        long minutes = seconds / 60;
        if (minutes < 60) return minutes + "分钟前";
        long hours = minutes / 60;
        if (hours < 24) return hours + "小时前";
        long days = hours / 24;
        if (days < 7) return days + "天前";
        return time.format(DateTimeFormatter.ofPattern("MM月dd日"));
    }
}
