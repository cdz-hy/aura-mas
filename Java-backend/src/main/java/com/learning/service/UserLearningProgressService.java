package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.entity.UserLearningProgress;
import com.learning.mapper.UserLearningProgressMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class UserLearningProgressService {

    private final UserLearningProgressMapper progressMapper;

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
}
