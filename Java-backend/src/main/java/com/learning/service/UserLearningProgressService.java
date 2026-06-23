package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.entity.DailyStudyTime;
import com.learning.entity.LearningResource;
import com.learning.entity.UserLearningProgress;
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

@Service
@RequiredArgsConstructor
public class UserLearningProgressService {

    private final UserLearningProgressMapper progressMapper;
    private final DailyStudyTimeMapper dailyStudyTimeMapper;
    private final LearningResourceMapper resourceMapper;
    @Lazy
    private final LearningPlanService planService;

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
    }

    @Transactional
    public void unmarkComplete(Long userId, Long planId, Long resourceId) {
        updateStatus(userId, planId, resourceId, 1);
        recalculatePlanProgress(userId, planId);
    }

    @Transactional
    public void recalculatePlanProgress(Long userId, Long planId) {
        List<UserLearningProgress> all = getByPlan(userId, planId);
        long completed = all.stream().filter(p -> p.getStatus() != null && p.getStatus() == 2).count();
        long total = resourceMapper.selectCount(
                new LambdaQueryWrapper<LearningResource>()
                        .eq(LearningResource::getPlanId, planId)
                        .ge(LearningResource::getStatus, 2));
        float progress = total > 0 ? (float) completed / total : 0;
        planService.updatePlanProgress(planId, progress);
    }
}
