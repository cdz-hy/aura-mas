package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.entity.DailyStudyTime;
import com.learning.entity.LearningResource;
import com.learning.entity.UserLearningProgress;
import com.learning.entity.LearningPlan;
import com.learning.mapper.DailyStudyTimeMapper;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.UserLearningProgressMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
public class UserLearningProgressService {

    private final UserLearningProgressMapper progressMapper;
    private final DailyStudyTimeMapper dailyStudyTimeMapper;
    private final LearningResourceMapper resourceMapper;
    @Lazy
    private final LearningPlanService planService;

    @org.springframework.beans.factory.annotation.Value("${python.backend.url:http://localhost:8002}")
    private String pythonBackendUrl;

    @org.springframework.beans.factory.annotation.Value("${internal.secret:change-this-internal-secret}")
    private String internalSecret;

    /**
     * 异步触发知识图谱掌握度分析（fire-and-forget，不阻塞主流程）
     */
    private void triggerMasteryUpdate(Long userId, Long resourceId, boolean completed) {
        triggerMasteryUpdateBatch(userId, java.util.List.of(resourceId), completed);
    }

    /**
     * 批量触发掌握度分析（串行处理，避免并发冲突和 429 限流）
     */
    private void triggerMasteryUpdateBatch(Long userId, List<Long> resourceIds, boolean completed) {
        if (resourceIds.isEmpty()) return;
        CompletableFuture.runAsync(() -> {
            try {
                var restTemplate = new org.springframework.web.client.RestTemplate();
                var headers = new org.springframework.http.HttpHeaders();
                headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
                headers.set("X-Service-Secret", internalSecret);
                var body = new java.util.HashMap<String, Object>();
                body.put("user_id", userId);
                body.put("resource_ids", resourceIds);
                body.put("completed", completed);
                var entity = new org.springframework.http.HttpEntity<>(body, headers);
                restTemplate.postForEntity(
                        pythonBackendUrl + "/api/ai/knowledge-graph/update-mastery-batch",
                        entity, String.class);
            } catch (Exception e) {
                // 非关键路径，静默失败
            }
        });
    }

    public List<UserLearningProgress> getByPlan(Long userId, Long planId) {
        return progressMapper.selectList(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .eq(UserLearningProgress::getPlanId, planId)
                        .orderByAsc(UserLearningProgress::getResourceId));
    }

    @Transactional
    public UserLearningProgress createOrUpdate(Long userId, Long planId, Long resourceId) {
        UserLearningProgress existing = progressMapper.selectOne(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .eq(UserLearningProgress::getPlanId, planId)
                        .eq(UserLearningProgress::getResourceId, resourceId));
        if (existing != null) {
            return existing;
        }
        UserLearningProgress progress = new UserLearningProgress();
        progress.setUserId(userId);
        progress.setPlanId(planId);
        progress.setResourceId(resourceId);
        progress.setStatus(0);
        progress.setDurationSeconds(0);
        progress.setCreatedAt(LocalDateTime.now());
        progress.setUpdatedAt(LocalDateTime.now());
        progressMapper.insert(progress);
        return progress;
    }

    @Transactional
    public void updateStatus(Long userId, Long planId, Long resourceId, Integer status) {
        UserLearningProgress existing = progressMapper.selectOne(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .eq(UserLearningProgress::getPlanId, planId)
                        .eq(UserLearningProgress::getResourceId, resourceId));
        if (existing != null) {
            existing.setStatus(status);
            existing.setLastAccessTime(LocalDateTime.now());
            existing.setUpdatedAt(LocalDateTime.now());
            progressMapper.updateById(existing);
        }
    }

    @Transactional
    public void heartbeat(Long userId, Long planId, Long resourceId, int elapsedSeconds) {
        if (elapsedSeconds <= 0) return;
        // resource_id is BIGINT UNSIGNED — reject temp/placeholder negative ids from the client
        if (userId == null || userId <= 0 || planId == null || planId <= 0
                || resourceId == null || resourceId <= 0) {
            return;
        }
        UserLearningProgress existing = progressMapper.selectOne(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .eq(UserLearningProgress::getPlanId, planId)
                        .eq(UserLearningProgress::getResourceId, resourceId));
        if (existing != null) {
            existing.setDurationSeconds((existing.getDurationSeconds() == null ? 0 : existing.getDurationSeconds()) + elapsedSeconds);
            existing.setLastAccessTime(LocalDateTime.now());
            if (existing.getStartTime() == null) {
                existing.setStartTime(LocalDateTime.now());
            }
            existing.setUpdatedAt(LocalDateTime.now());
            progressMapper.updateById(existing);
        } else {
            UserLearningProgress progress = new UserLearningProgress();
            progress.setUserId(userId);
            progress.setPlanId(planId);
            progress.setResourceId(resourceId);
            progress.setStatus(1);
            progress.setStartTime(LocalDateTime.now());
            progress.setLastAccessTime(LocalDateTime.now());
            progress.setDurationSeconds(elapsedSeconds);
            progress.setCreatedAt(LocalDateTime.now());
            progress.setUpdatedAt(LocalDateTime.now());
            progressMapper.insert(progress);
        }

        // 按天累加学习时长
        LocalDate today = LocalDate.now();
        DailyStudyTime daily = dailyStudyTimeMapper.selectOne(
                new LambdaQueryWrapper<DailyStudyTime>()
                        .eq(DailyStudyTime::getUserId, userId)
                        .eq(DailyStudyTime::getStudyDate, today));
        if (daily != null) {
            daily.setDurationSeconds(daily.getDurationSeconds() + elapsedSeconds);
            dailyStudyTimeMapper.updateById(daily);
        } else {
            DailyStudyTime newDaily = new DailyStudyTime();
            newDaily.setUserId(userId);
            newDaily.setStudyDate(today);
            newDaily.setDurationSeconds(elapsedSeconds);
            newDaily.setCreatedAt(LocalDateTime.now());
            newDaily.setUpdatedAt(LocalDateTime.now());
            dailyStudyTimeMapper.insert(newDaily);
        }
    }

    @Transactional
    public void markComplete(Long userId, Long planId, Long resourceId) {
        UserLearningProgress existing = progressMapper.selectOne(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .eq(UserLearningProgress::getPlanId, planId)
                        .eq(UserLearningProgress::getResourceId, resourceId));
        if (existing != null) {
            existing.setStatus(2);
            existing.setCompleteTime(LocalDateTime.now());
            existing.setLastAccessTime(LocalDateTime.now());
            existing.setUpdatedAt(LocalDateTime.now());
            progressMapper.updateById(existing);
        } else {
            UserLearningProgress progress = new UserLearningProgress();
            progress.setUserId(userId);
            progress.setPlanId(planId);
            progress.setResourceId(resourceId);
            progress.setStatus(2);
            progress.setDurationSeconds(0);
            progress.setStartTime(LocalDateTime.now());
            progress.setCompleteTime(LocalDateTime.now());
            progress.setLastAccessTime(LocalDateTime.now());
            progress.setCreatedAt(LocalDateTime.now());
            progress.setUpdatedAt(LocalDateTime.now());
            progressMapper.insert(progress);
        }
        recalculatePlanProgress(userId, planId);
        // 异步触发知识图谱掌握度分析
        triggerMasteryUpdate(userId, resourceId, true);
    }

    @Transactional
    public void unmarkComplete(Long userId, Long planId, Long resourceId) {
        updateStatus(userId, planId, resourceId, 1);
        recalculatePlanProgress(userId, planId);
        // 异步触发知识图谱掌握度分析
        triggerMasteryUpdate(userId, resourceId, false);
    }

    /**
     * 一键标记计划下所有已生成资源为完成
     * 只标记 status >= 2（已就绪）的资源，排除正在生成和失败的
     * 批量更新后只重算一次进度，避免 O(N^2)
     */
    @Transactional
    public void markAllComplete(Long userId, Long planId) {
        List<LearningResource> resources = resourceMapper.selectList(
                new LambdaQueryWrapper<LearningResource>()
                        .eq(LearningResource::getPlanId, planId)
                        .ge(LearningResource::getStatus, 2));
        if (resources.isEmpty()) return;

        // Batch upsert all resource progress records
        List<Long> updatedResourceIds = new java.util.ArrayList<>();
        for (LearningResource r : resources) {
            UserLearningProgress existing = progressMapper.selectOne(
                    new LambdaQueryWrapper<UserLearningProgress>()
                            .eq(UserLearningProgress::getUserId, userId)
                            .eq(UserLearningProgress::getPlanId, planId)
                            .eq(UserLearningProgress::getResourceId, r.getId()));
            if (existing != null) {
                if (existing.getStatus() != null && existing.getStatus() == 2) continue; // already complete
                existing.setStatus(2);
                existing.setCompleteTime(LocalDateTime.now());
                existing.setLastAccessTime(LocalDateTime.now());
                existing.setUpdatedAt(LocalDateTime.now());
                progressMapper.updateById(existing);
                updatedResourceIds.add(r.getId());
            } else {
                UserLearningProgress progress = new UserLearningProgress();
                progress.setUserId(userId);
                progress.setPlanId(planId);
                progress.setResourceId(r.getId());
                progress.setStatus(2);
                progress.setDurationSeconds(0);
                progress.setStartTime(LocalDateTime.now());
                progress.setCompleteTime(LocalDateTime.now());
                progress.setLastAccessTime(LocalDateTime.now());
                progress.setCreatedAt(LocalDateTime.now());
                progress.setUpdatedAt(LocalDateTime.now());
                progressMapper.insert(progress);
                updatedResourceIds.add(r.getId());
            }
        }
        // Recalculate only once at the end
        recalculatePlanProgress(userId, planId);
        // Async trigger mastery analysis (single batch, serial processing)
        triggerMasteryUpdateBatch(userId, updatedResourceIds, true);
    }

    /**
     * 批量获取多个计划的进度摘要
     * 返回 planId -> {completed, total, progress(0-1.0), isCompleted}
     * 使用 IN 批量查询，仅 2 次 SQL（不论多少个 plan）
     */
    public java.util.Map<String, Object> getProgressSummary(Long userId, List<Long> planIds) {
        java.util.Map<String, Object> result = new java.util.HashMap<>();
        if (planIds == null || planIds.isEmpty()) return result;

        // 1. Batch fetch all valid resources (status >= 2) for all plans
        List<LearningResource> allResources = resourceMapper.selectList(
                new LambdaQueryWrapper<LearningResource>()
                        .in(LearningResource::getPlanId, planIds)
                        .ge(LearningResource::getStatus, 2));

        // Group by planId
        java.util.Map<Long, java.util.Set<Long>> planValidIds = new java.util.HashMap<>();
        for (LearningResource r : allResources) {
            planValidIds.computeIfAbsent(r.getPlanId(), k -> new java.util.HashSet<>()).add(r.getId());
        }

        // 2. Batch fetch all completed progress for all plans
        List<UserLearningProgress> allProgress = progressMapper.selectList(
                new LambdaQueryWrapper<UserLearningProgress>()
                        .eq(UserLearningProgress::getUserId, userId)
                        .in(UserLearningProgress::getPlanId, planIds)
                        .eq(UserLearningProgress::getStatus, 2));

        // Group by planId
        java.util.Map<Long, List<UserLearningProgress>> planProgress = new java.util.HashMap<>();
        for (UserLearningProgress p : allProgress) {
            planProgress.computeIfAbsent(p.getPlanId(), k -> new java.util.ArrayList<>()).add(p);
        }

        // 3. Build summary for each plan
        for (Long planId : planIds) {
            java.util.Map<String, Object> summary = new java.util.HashMap<>();
            java.util.Set<Long> validIds = planValidIds.getOrDefault(planId, java.util.Collections.emptySet());
            int total = validIds.size();

            int completed = 0;
            List<UserLearningProgress> progresses = planProgress.getOrDefault(planId, java.util.Collections.emptyList());
            for (UserLearningProgress p : progresses) {
                if (validIds.contains(p.getResourceId())) completed++;
            }

            float progress = total > 0 ? Math.min(1.0f, (float) completed / total) : 0.0f;
            summary.put("completed", completed);
            summary.put("total", total);
            summary.put("progress", progress);
            summary.put("isCompleted", progress >= 1.0f && total > 0);
            result.put(String.valueOf(planId), summary);
        }
        return result;
    }

    /**
     * 查询单个计划进度
     */
    public java.util.Map<String, Object> getPlanProgress(Long userId, Long planId) {
        return getProgressSummary(userId, java.util.List.of(planId));
    }

    @Transactional
    public void recalculatePlanProgress(Long userId, Long planId) {
        List<UserLearningProgress> all = getByPlan(userId, planId);

        java.util.Set<Long> validResourceIds = new java.util.HashSet<>();
        List<LearningResource> resources = resourceMapper.selectList(
                new LambdaQueryWrapper<LearningResource>()
                        .eq(LearningResource::getPlanId, planId)
                        .ge(LearningResource::getStatus, 2));
        for (LearningResource r : resources) {
            validResourceIds.add(r.getId());
        }

        long completed = 0;
        for (UserLearningProgress p : all) {
            if (p.getStatus() != null && p.getStatus() == 2 && validResourceIds.contains(p.getResourceId())) {
                completed++;
            }
        }

        long total = validResourceIds.size();
        float progress = total > 0 ? Math.min(1.0f, (float) completed / total) : 0.0f;

        planService.updatePlanProgress(planId, progress);

        // Auto-manage plan status based on progress
        // All resources complete → status=4 (completed)
        // Some resources unmarked while status=4 → revert to 3 (learning)
        if (total > 0) {
            LearningPlan plan = planService.getPlanByIdInternal(planId);
            if (plan != null) {
                int currentStatus = plan.getStatus() != null ? plan.getStatus() : 0;
                if (progress >= 1.0f && currentStatus != 4) {
                    planService.updatePlanStatus(planId, 4);
                } else if (progress < 1.0f && currentStatus == 4) {
                    planService.updatePlanStatus(planId, 3);
                }
            }
        }
    }
}
