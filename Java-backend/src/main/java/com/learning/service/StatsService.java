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
    private final FlashcardMapper flashcardMapper;
    private final AiDialogueMapper aiDialogueMapper;
    private final UserProfileMapper userProfileMapper;

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

        // 今日学习时长（从 DailyStudyTime 表获取，与心跳写入一致）
        DailyStudyTime todayDaily = dailyStudyTimeMapper.selectOne(
                new LambdaQueryWrapper<DailyStudyTime>()
                        .eq(DailyStudyTime::getUserId, userId)
                        .eq(DailyStudyTime::getStudyDate, LocalDate.now()));
        int todaySeconds = todayDaily != null && todayDaily.getDurationSeconds() != null
                ? todayDaily.getDurationSeconds() : 0;
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

    // ======================== 答题详细分析 ========================
    public Map<String, Object> getQuizAnalysis(Long userId) {
        Map<String, Object> result = new HashMap<>();

        List<QuizRecord> records = quizRecordMapper.selectList(
                new LambdaQueryWrapper<QuizRecord>()
                        .eq(QuizRecord::getUserId, userId)
                        .orderByDesc(QuizRecord::getAnswerTime));

        if (records.isEmpty()) {
            result.put("byQuestionType", Collections.emptyList());
            result.put("byDifficulty", Collections.emptyList());
            result.put("dailyAccuracy", Collections.emptyList());
            Map<String, Object> trend = new HashMap<>();
            trend.put("direction", "stable");
            trend.put("changePercent", 0);
            result.put("recentTrend", trend);
            return result;
        }

        // 按题型分组
        Map<String, List<QuizRecord>> byType = records.stream()
                .filter(r -> r.getQuestionType() != null)
                .collect(Collectors.groupingBy(QuizRecord::getQuestionType));

        List<Map<String, Object>> byQuestionType = new ArrayList<>();
        for (Map.Entry<String, List<QuizRecord>> entry : byType.entrySet()) {
            List<QuizRecord> group = entry.getValue();
            long correct = group.stream().filter(r -> r.getIsCorrect() != null && r.getIsCorrect() == 1).count();
            Map<String, Object> item = new HashMap<>();
            item.put("type", entry.getKey());
            item.put("total", group.size());
            item.put("correct", correct);
            item.put("accuracy", group.size() > 0 ? Math.round((double) correct / group.size() * 1000) / 10.0 : 0);
            byQuestionType.add(item);
        }
        result.put("byQuestionType", byQuestionType);

        // 按难度分组
        Map<Integer, List<QuizRecord>> byDiff = records.stream()
                .filter(r -> r.getDifficulty() != null)
                .collect(Collectors.groupingBy(QuizRecord::getDifficulty));

        List<Map<String, Object>> byDifficulty = new ArrayList<>();
        for (int d = 1; d <= 5; d++) {
            List<QuizRecord> group = byDiff.getOrDefault(d, Collections.emptyList());
            long correct = group.stream().filter(r -> r.getIsCorrect() != null && r.getIsCorrect() == 1).count();
            Map<String, Object> item = new HashMap<>();
            item.put("difficulty", d);
            item.put("total", group.size());
            item.put("correct", correct);
            item.put("accuracy", group.size() > 0 ? Math.round((double) correct / group.size() * 1000) / 10.0 : 0);
            byDifficulty.add(item);
        }
        result.put("byDifficulty", byDifficulty);

        // 每日正确率趋势（最近30天）
        LocalDate thirtyDaysAgo = LocalDate.now().minusDays(30);
        Map<LocalDate, List<QuizRecord>> byDate = records.stream()
                .filter(r -> r.getAnswerTime() != null && r.getAnswerTime().toLocalDate().isAfter(thirtyDaysAgo))
                .collect(Collectors.groupingBy(r -> r.getAnswerTime().toLocalDate()));

        List<Map<String, Object>> dailyAccuracy = new ArrayList<>();
        for (int i = 29; i >= 0; i--) {
            LocalDate date = LocalDate.now().minusDays(i);
            List<QuizRecord> dayRecords = byDate.getOrDefault(date, Collections.emptyList());
            long correct = dayRecords.stream().filter(r -> r.getIsCorrect() != null && r.getIsCorrect() == 1).count();
            Map<String, Object> day = new HashMap<>();
            day.put("date", date.toString());
            day.put("total", dayRecords.size());
            day.put("accuracy", dayRecords.size() > 0 ? Math.round((double) correct / dayRecords.size() * 1000) / 10.0 : 0);
            dailyAccuracy.add(day);
        }
        result.put("dailyAccuracy", dailyAccuracy);

        // 近期趋势（最近7天 vs 前7天）
        LocalDate sevenDaysAgo = LocalDate.now().minusDays(7);
        LocalDate fourteenDaysAgo = LocalDate.now().minusDays(14);
        long recentCorrect = records.stream()
                .filter(r -> r.getAnswerTime() != null && r.getAnswerTime().toLocalDate().isAfter(sevenDaysAgo))
                .filter(r -> r.getIsCorrect() != null && r.getIsCorrect() == 1).count();
        long recentTotal = records.stream()
                .filter(r -> r.getAnswerTime() != null && r.getAnswerTime().toLocalDate().isAfter(sevenDaysAgo))
                .count();
        long prevCorrect = records.stream()
                .filter(r -> r.getAnswerTime() != null &&
                        r.getAnswerTime().toLocalDate().isAfter(fourteenDaysAgo) &&
                        r.getAnswerTime().toLocalDate().isBefore(sevenDaysAgo.plusDays(1)))
                .filter(r -> r.getIsCorrect() != null && r.getIsCorrect() == 1).count();
        long prevTotal = records.stream()
                .filter(r -> r.getAnswerTime() != null &&
                        r.getAnswerTime().toLocalDate().isAfter(fourteenDaysAgo) &&
                        r.getAnswerTime().toLocalDate().isBefore(sevenDaysAgo.plusDays(1)))
                .count();

        double recentAcc = recentTotal > 0 ? (double) recentCorrect / recentTotal : 0;
        double prevAcc = prevTotal > 0 ? (double) prevCorrect / prevTotal : 0;
        double changePercent = prevAcc > 0 ? Math.round((recentAcc - prevAcc) / prevAcc * 1000) / 10.0 : 0;
        String direction = changePercent > 5 ? "up" : (changePercent < -5 ? "down" : "stable");

        Map<String, Object> recentTrend = new HashMap<>();
        recentTrend.put("direction", direction);
        recentTrend.put("changePercent", changePercent);
        result.put("recentTrend", recentTrend);

        return result;
    }

    // ======================== 学习热力图 ========================
    public Map<String, Object> getStudyHeatmap(Long userId, int days) {
        Map<String, Object> result = new HashMap<>();

        LocalDate startDate = LocalDate.now().minusDays(days);
        List<DailyStudyTime> dailyData = dailyStudyTimeMapper.selectList(
                new LambdaQueryWrapper<DailyStudyTime>()
                        .eq(DailyStudyTime::getUserId, userId)
                        .ge(DailyStudyTime::getStudyDate, startDate)
                        .orderByAsc(DailyStudyTime::getStudyDate));

        Map<LocalDate, Integer> dailyMap = new HashMap<>();
        for (DailyStudyTime d : dailyData) {
            dailyMap.put(d.getStudyDate(), d.getDurationSeconds());
        }

        // 生成热力图数据
        List<Map<String, Object>> heatmapData = new ArrayList<>();
        for (int i = days - 1; i >= 0; i--) {
            LocalDate date = LocalDate.now().minusDays(i);
            int seconds = dailyMap.getOrDefault(date, 0);
            int minutes = seconds / 60;
            int level = 0;
            if (minutes > 0 && minutes <= 30) level = 1;
            else if (minutes > 30 && minutes <= 60) level = 2;
            else if (minutes > 60 && minutes <= 120) level = 3;
            else if (minutes > 120) level = 4;

            Map<String, Object> day = new HashMap<>();
            day.put("date", date.toString());
            day.put("minutes", minutes);
            day.put("level", level);
            heatmapData.add(day);
        }
        result.put("dailyData", heatmapData);

        // 计算连续天数
        int currentStreak = 0;
        int longestStreak = 0;
        int tempStreak = 0;
        int totalActiveDays = 0;

        for (int i = 0; i < days; i++) {
            LocalDate date = LocalDate.now().minusDays(i);
            int minutes = dailyMap.getOrDefault(date, 0) / 60;
            if (minutes > 0) {
                totalActiveDays++;
                if (i == currentStreak) currentStreak++;
                tempStreak++;
                longestStreak = Math.max(longestStreak, tempStreak);
            } else {
                tempStreak = 0;
            }
        }

        result.put("currentStreak", currentStreak);
        result.put("longestStreak", longestStreak);
        result.put("totalActiveDays", totalActiveDays);

        return result;
    }

    // ======================== 闪卡复习统计 ========================
    public Map<String, Object> getFlashcardStats(Long userId) {
        Map<String, Object> result = new HashMap<>();

        List<Flashcard> cards = flashcardMapper.selectList(
                new LambdaQueryWrapper<Flashcard>()
                        .eq(Flashcard::getUserId, userId));

        LocalDateTime now = LocalDateTime.now();

        long totalCards = cards.size();
        long dueToday = cards.stream()
                .filter(c -> c.getNextReviewAt() != null && c.getNextReviewAt().isBefore(now))
                .count();
        long mastered = cards.stream()
                .filter(c -> c.getReviewCount() != null && c.getReviewCount() >= 5 &&
                        c.getEaseFactor() != null && c.getEaseFactor() >= 2.5)
                .count();
        long learning = cards.stream()
                .filter(c -> c.getReviewCount() != null && c.getReviewCount() > 0 &&
                        !(c.getReviewCount() >= 5 && c.getEaseFactor() != null && c.getEaseFactor() >= 2.5))
                .count();
        long newCards = cards.stream()
                .filter(c -> c.getReviewCount() == null || c.getReviewCount() == 0)
                .count();

        double avgEaseFactor = cards.stream()
                .filter(c -> c.getEaseFactor() != null)
                .mapToDouble(Flashcard::getEaseFactor)
                .average()
                .orElse(2.5);

        result.put("totalCards", totalCards);
        result.put("dueToday", dueToday);
        result.put("mastered", mastered);
        result.put("learning", learning);
        result.put("newCards", newCards);
        result.put("avgEaseFactor", Math.round(avgEaseFactor * 100) / 100.0);

        // 复习历史（简化：按easeFactor区间分组）
        List<Map<String, Object>> easeFactorDistribution = new ArrayList<>();
        int[] ranges = {0, 150, 200, 250, 300};
        String[] labels = {"<1.5", "1.5-2.0", "2.0-2.5", "2.5-3.0", ">3.0"};
        for (int i = 0; i < ranges.length; i++) {
            int min = ranges[i];
            int max = i < ranges.length - 1 ? ranges[i + 1] : 999;
            long count = cards.stream()
                    .filter(c -> c.getEaseFactor() != null &&
                            c.getEaseFactor() * 100 >= min &&
                            c.getEaseFactor() * 100 < max)
                    .count();
            Map<String, Object> range = new HashMap<>();
            range.put("label", labels[i]);
            range.put("count", count);
            easeFactorDistribution.add(range);
        }
        result.put("easeFactorDistribution", easeFactorDistribution);

        return result;
    }

    // ======================== AI对话分析 ========================
    public Map<String, Object> getAiInteractionStats(Long userId) {
        Map<String, Object> result = new HashMap<>();

        List<AiDialogue> dialogues = aiDialogueMapper.selectList(
                new LambdaQueryWrapper<AiDialogue>()
                        .eq(AiDialogue::getUserId, userId)
                        .orderByDesc(AiDialogue::getDialogueTime));

        long totalDialogues = dialogues.size();
        result.put("totalDialogues", totalDialogues);

        // 按意图类型分组
        Map<String, Long> byIntent = dialogues.stream()
                .filter(d -> d.getIntentType() != null)
                .collect(Collectors.groupingBy(AiDialogue::getIntentType, Collectors.counting()));

        List<Map<String, Object>> byIntentType = new ArrayList<>();
        for (Map.Entry<String, Long> entry : byIntent.entrySet()) {
            Map<String, Object> item = new HashMap<>();
            item.put("intent", entry.getKey());
            item.put("count", entry.getValue());
            item.put("percentage", totalDialogues > 0 ? Math.round((double) entry.getValue() / totalDialogues * 1000) / 10.0 : 0);
            byIntentType.add(item);
        }
        result.put("byIntentType", byIntentType);

        // 每日对话次数（最近30天）
        LocalDate thirtyDaysAgo = LocalDate.now().minusDays(30);
        Map<LocalDate, Long> dailyCount = dialogues.stream()
                .filter(d -> d.getDialogueTime() != null && d.getDialogueTime().toLocalDate().isAfter(thirtyDaysAgo))
                .collect(Collectors.groupingBy(d -> d.getDialogueTime().toLocalDate(), Collectors.counting()));

        List<Map<String, Object>> dailyDialogues = new ArrayList<>();
        for (int i = 29; i >= 0; i--) {
            LocalDate date = LocalDate.now().minusDays(i);
            Map<String, Object> day = new HashMap<>();
            day.put("date", date.toString());
            day.put("count", dailyCount.getOrDefault(date, 0L));
            dailyDialogues.add(day);
        }
        result.put("dailyDialogues", dailyDialogues);

        // 平均会话长度
        Map<String, List<AiDialogue>> bySession = dialogues.stream()
                .filter(d -> d.getSessionId() != null)
                .collect(Collectors.groupingBy(AiDialogue::getSessionId));
        double avgSessionLength = bySession.values().stream()
                .mapToInt(List::size)
                .average()
                .orElse(0);
        result.put("avgSessionLength", Math.round(avgSessionLength * 10) / 10.0);

        return result;
    }

    // ======================== 知识掌握度 ========================
    public Map<String, Object> getKnowledgeMastery(Long userId) {
        Map<String, Object> result = new HashMap<>();

        // 从UserProfile获取画像数据
        UserProfile profile = userProfileMapper.selectOne(
                new LambdaQueryWrapper<UserProfile>()
                        .eq(UserProfile::getUserId, userId)
                        .eq(UserProfile::getIsCurrent, 1)
                        .last("LIMIT 1"));

        List<String> mastered = new ArrayList<>();
        List<String> weakAreas = new ArrayList<>();
        List<String> interests = new ArrayList<>();
        Map<String, Object> performance = new HashMap<>();
        Map<String, Object> learningStyle = new HashMap<>();
        learningStyle.put("visual_vs_verbal", 0.0);
        learningStyle.put("active_vs_reflective", 0.0);
        learningStyle.put("sensing_vs_intuitive", 0.0);
        learningStyle.put("sequential_vs_global", 0.0);

        if (profile != null && profile.getLearningBehavior() != null) {
            try {
                String json = profile.getLearningBehavior();
                // 简单JSON解析
                if (json.contains("\"knowledge_base\"")) {
                    List<String> kb = extractJsonArray(json, "knowledge_base");
                    mastered.addAll(kb);
                }
                if (json.contains("\"weak_areas\"")) {
                    List<String> wa = extractJsonArray(json, "weak_areas");
                    weakAreas.addAll(wa);
                }
                if (json.contains("\"interest_tags\"")) {
                    List<String> it = extractJsonArray(json, "interest_tags");
                    interests.addAll(it);
                }

                performance.put("learningSpeed", extractJsonDouble(json, "learning_speed", 0.5));
                performance.put("engagement", extractJsonDouble(json, "engagement_level", 0.5));
                performance.put("quizAccuracy", extractJsonDouble(json, "quiz_accuracy", 0.0));
                performance.put("completionRate", extractJsonDouble(json, "completion_rate", 0.0));

                // 学习风格维度
                learningStyle.put("visual_vs_verbal", extractJsonDouble(json, "visual_vs_verbal", 0.0));
                learningStyle.put("active_vs_reflective", extractJsonDouble(json, "active_vs_reflective", 0.0));
                learningStyle.put("sensing_vs_intuitive", extractJsonDouble(json, "sensing_vs_intuitive", 0.0));
                learningStyle.put("sequential_vs_global", extractJsonDouble(json, "sequential_vs_global", 0.0));
            } catch (Exception e) {
                log.error("解析用户画像失败", e);
            }
        }

        result.put("mastered", mastered);
        result.put("weakAreas", weakAreas);
        result.put("interests", interests);
        result.put("performance", performance);
        result.put("learningStyle", learningStyle);

        return result;
    }

    // ======================== 学习效率时段分析 ========================
    public Map<String, Object> getStudyEfficiency(Long userId) {
        Map<String, Object> result = new HashMap<>();

        // 按小时统计学习时长和会话次数（从 learning_duration 的 start_time 提取小时）
        List<LearningDuration> allDurations = durationMapper.selectList(
                new LambdaQueryWrapper<LearningDuration>()
                        .eq(LearningDuration::getUserId, userId)
                        .isNotNull(LearningDuration::getStartTime));

        // 按小时统计学习时长
        int[] studyMinutesByHour = new int[24];
        int[] sessionCountByHour = new int[24];
        for (LearningDuration d : allDurations) {
            int hour = d.getStartTime().getHour();
            sessionCountByHour[hour]++;
            studyMinutesByHour[hour] += (d.getDurationSeconds() != null ? d.getDurationSeconds() : 0) / 60;
        }

        // 按小时统计答题正确率
        List<QuizRecord> allQuizzes = quizRecordMapper.selectList(
                new LambdaQueryWrapper<QuizRecord>()
                        .eq(QuizRecord::getUserId, userId)
                        .isNotNull(QuizRecord::getAnswerTime));

        int[] quizTotalByHour = new int[24];
        int[] quizCorrectByHour = new int[24];
        for (QuizRecord q : allQuizzes) {
            int hour = q.getAnswerTime().getHour();
            quizTotalByHour[hour]++;
            if (q.getIsCorrect() != null && q.getIsCorrect() == 1) {
                quizCorrectByHour[hour]++;
            }
        }

        // 组装 24 小时数据
        List<Map<String, Object>> hourlyData = new ArrayList<>();
        int bestStudyHour = 0;
        int bestQuizHour = 0;
        int maxStudyMin = 0;
        double maxQuizAcc = 0;

        for (int h = 0; h < 24; h++) {
            double accuracy = quizTotalByHour[h] > 0
                    ? Math.round((double) quizCorrectByHour[h] / quizTotalByHour[h] * 1000) / 10.0
                    : 0;

            Map<String, Object> hour = new HashMap<>();
            hour.put("hour", h);
            hour.put("studyMinutes", studyMinutesByHour[h]);
            hour.put("sessionCount", sessionCountByHour[h]);
            hour.put("quizTotal", quizTotalByHour[h]);
            hour.put("quizCorrect", quizCorrectByHour[h]);
            hour.put("accuracy", accuracy);
            hourlyData.add(hour);

            if (studyMinutesByHour[h] > maxStudyMin) {
                maxStudyMin = studyMinutesByHour[h];
                bestStudyHour = h;
            }
            if (quizTotalByHour[h] >= 5 && accuracy > maxQuizAcc) {
                maxQuizAcc = accuracy;
                bestQuizHour = h;
            }
        }

        result.put("hourlyData", hourlyData);
        result.put("bestStudyHour", bestStudyHour);
        result.put("bestQuizHour", bestQuizHour);
        result.put("bestQuizAccuracy", maxQuizAcc);

        return result;
    }

    // ======================== 周对比 ========================
    public Map<String, Object> getWeekComparison(Long userId) {
        Map<String, Object> result = new HashMap<>();

        LocalDate today = LocalDate.now();
        LocalDate thisMonday = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
        LocalDate lastMonday = thisMonday.minusDays(7);

        // 学习时长对比
        List<DailyStudyTime> thisWeekData = dailyStudyTimeMapper.selectList(
                new LambdaQueryWrapper<DailyStudyTime>()
                        .eq(DailyStudyTime::getUserId, userId)
                        .ge(DailyStudyTime::getStudyDate, thisMonday));
        List<DailyStudyTime> lastWeekData = dailyStudyTimeMapper.selectList(
                new LambdaQueryWrapper<DailyStudyTime>()
                        .eq(DailyStudyTime::getUserId, userId)
                        .ge(DailyStudyTime::getStudyDate, lastMonday)
                        .lt(DailyStudyTime::getStudyDate, thisMonday));

        int thisWeekMinutes = thisWeekData.stream()
                .mapToInt(d -> (d.getDurationSeconds() != null ? d.getDurationSeconds() : 0) / 60).sum();
        int lastWeekMinutes = lastWeekData.stream()
                .mapToInt(d -> (d.getDurationSeconds() != null ? d.getDurationSeconds() : 0) / 60).sum();

        int thisActiveDays = (int) thisWeekData.stream()
                .filter(d -> d.getDurationSeconds() != null && d.getDurationSeconds() > 0).count();
        int lastActiveDays = (int) lastWeekData.stream()
                .filter(d -> d.getDurationSeconds() != null && d.getDurationSeconds() > 0).count();

        // 答题正确率对比
        List<QuizRecord> thisWeekQuizzes = quizRecordMapper.selectList(
                new LambdaQueryWrapper<QuizRecord>()
                        .eq(QuizRecord::getUserId, userId)
                        .isNotNull(QuizRecord::getAnswerTime)
                        .ge(QuizRecord::getAnswerTime, thisMonday.atStartOfDay()));
        List<QuizRecord> lastWeekQuizzes = quizRecordMapper.selectList(
                new LambdaQueryWrapper<QuizRecord>()
                        .eq(QuizRecord::getUserId, userId)
                        .isNotNull(QuizRecord::getAnswerTime)
                        .ge(QuizRecord::getAnswerTime, lastMonday.atStartOfDay())
                        .lt(QuizRecord::getAnswerTime, thisMonday.atStartOfDay()));

        double thisWeekAcc = thisWeekQuizzes.size() > 0
                ? Math.round((double) thisWeekQuizzes.stream()
                .filter(q -> q.getIsCorrect() != null && q.getIsCorrect() == 1).count()
                / thisWeekQuizzes.size() * 1000) / 10.0 : 0;
        double lastWeekAcc = lastWeekQuizzes.size() > 0
                ? Math.round((double) lastWeekQuizzes.stream()
                .filter(q -> q.getIsCorrect() != null && q.getIsCorrect() == 1).count()
                / lastWeekQuizzes.size() * 1000) / 10.0 : 0;

        // 变化百分比
        int studyChange = lastWeekMinutes > 0
                ? (int) Math.round((double) (thisWeekMinutes - lastWeekMinutes) / lastWeekMinutes * 100) : 0;
        double accChange = lastWeekAcc > 0
                ? Math.round((thisWeekAcc - lastWeekAcc) / lastWeekAcc * 1000) / 10.0 : 0;

        Map<String, Object> studyMinutes = new HashMap<>();
        studyMinutes.put("thisWeek", thisWeekMinutes);
        studyMinutes.put("lastWeek", lastWeekMinutes);
        studyMinutes.put("change", studyChange);

        Map<String, Object> quizAccuracy = new HashMap<>();
        quizAccuracy.put("thisWeek", thisWeekAcc);
        quizAccuracy.put("lastWeek", lastWeekAcc);
        quizAccuracy.put("change", accChange);

        Map<String, Object> activeDays = new HashMap<>();
        activeDays.put("thisWeek", thisActiveDays);
        activeDays.put("lastWeek", lastActiveDays);

        result.put("studyMinutes", studyMinutes);
        result.put("quizAccuracy", quizAccuracy);
        result.put("activeDays", activeDays);

        return result;
    }

    // ======================== 聚合全部分析数据 ========================
    public Map<String, Object> getAnalyticsData(Long userId) {
        Map<String, Object> result = new HashMap<>();

        try {
            result.put("overview", getDashboardStats(userId));
        } catch (Exception e) {
            log.error("获取overview失败", e);
            result.put("overview", new HashMap<>());
        }

        try {
            result.put("quizAnalysis", getQuizAnalysis(userId));
        } catch (Exception e) {
            log.error("获取quizAnalysis失败", e);
            result.put("quizAnalysis", new HashMap<>());
        }

        try {
            result.put("heatmap", getStudyHeatmap(userId, 180));
        } catch (Exception e) {
            log.error("获取heatmap失败", e);
            result.put("heatmap", new HashMap<>());
        }

        try {
            result.put("flashcardStats", getFlashcardStats(userId));
        } catch (Exception e) {
            log.error("获取flashcardStats失败", e);
            result.put("flashcardStats", new HashMap<>());
        }

        try {
            result.put("aiInteraction", getAiInteractionStats(userId));
        } catch (Exception e) {
            log.error("获取aiInteraction失败", e);
            result.put("aiInteraction", new HashMap<>());
        }

        try {
            result.put("knowledgeMastery", getKnowledgeMastery(userId));
        } catch (Exception e) {
            log.error("获取knowledgeMastery失败", e);
            result.put("knowledgeMastery", new HashMap<>());
        }

        try {
            result.put("studyEfficiency", getStudyEfficiency(userId));
        } catch (Exception e) {
            log.error("获取studyEfficiency失败", e);
            result.put("studyEfficiency", new HashMap<>());
        }

        try {
            result.put("weekComparison", getWeekComparison(userId));
        } catch (Exception e) {
            log.error("获取weekComparison失败", e);
            result.put("weekComparison", new HashMap<>());
        }

        return result;
    }

    // ======================== JSON解析辅助方法 ========================
    private List<String> extractJsonArray(String json, String key) {
        List<String> result = new ArrayList<>();
        try {
            int start = json.indexOf("\"" + key + "\"");
            if (start < 0) return result;
            start = json.indexOf("[", start);
            int end = json.indexOf("]", start);
            if (start < 0 || end < 0) return result;
            String arrayStr = json.substring(start + 1, end).trim();
            if (arrayStr.isEmpty()) return result;
            // 分割引号包围的字符串
            String[] items = arrayStr.split(",");
            for (String item : items) {
                String trimmed = item.trim().replace("\"", "");
                if (!trimmed.isEmpty()) {
                    result.add(trimmed);
                }
            }
        } catch (Exception e) {
            log.error("解析JSON数组失败: " + key, e);
        }
        return result;
    }

    private double extractJsonDouble(String json, String key, double defaultValue) {
        try {
            int start = json.indexOf("\"" + key + "\"");
            if (start < 0) return defaultValue;
            start = json.indexOf(":", start);
            if (start < 0) return defaultValue;
            start++;
            int end = start;
            while (end < json.length() && (Character.isDigit(json.charAt(end)) || json.charAt(end) == '.' || json.charAt(end) == '-')) {
                end++;
            }
            String numStr = json.substring(start, end).trim();
            return Double.parseDouble(numStr);
        } catch (Exception e) {
            return defaultValue;
        }
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
