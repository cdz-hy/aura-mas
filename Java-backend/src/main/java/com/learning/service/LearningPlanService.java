package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.common.ErrorCode;
import com.learning.common.PageResult;
import com.learning.dto.PlanCreateRequest;
import com.learning.entity.*;
import com.learning.exception.BusinessException;
import com.learning.mapper.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class LearningPlanService {

    private final LearningPlanMapper planMapper;
    private final LearningResourceMapper resourceMapper;
    private final AiDialogueMapper dialogueMapper;
    private final QuizRecordMapper quizRecordMapper;
    private final LearningDurationMapper durationMapper;
    private final UserLearningProgressMapper progressMapper;
    private final ResourceGenerationTaskMapper generationTaskMapper;
    private final ObjectMapper objectMapper;

    @Transactional
    public LearningPlan createPlan(Long userId, PlanCreateRequest request) {
        LearningPlan plan = new LearningPlan();
        plan.setTitle(request.getTitle());
        plan.setLearningGoal(toJson(request.getLearningGoal()));
        plan.setPlanConfig(toJson(request.getPlanConfig()));
        plan.setUserId(userId);
        plan.setStatus(0);
        plan.setProgress(0.0f);
        plan.setCreatedAt(LocalDateTime.now());
        plan.setUpdatedAt(LocalDateTime.now());
        planMapper.insert(plan);
        return plan;
    }

    public LearningPlan getPlanById(Long planId, Long userId) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null || !plan.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        return plan;
    }

    public PageResult<LearningPlan> getUserPlans(Long userId, int page, int size) {
        Page<LearningPlan> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<LearningPlan> wrapper = new LambdaQueryWrapper<LearningPlan>()
                .eq(LearningPlan::getUserId, userId)
                .orderByDesc(LearningPlan::getCreatedAt);

        Page<LearningPlan> result = planMapper.selectPage(pageParam, wrapper);
        List<LearningPlan> plans = result.getRecords();

        // 计算每个计划的展示状态（基于资源生成情况）
        if (!plans.isEmpty()) {
            List<Long> planIds = plans.stream().map(LearningPlan::getId).collect(Collectors.toList());
            List<LearningResource> allResources = resourceMapper.selectList(
                    new LambdaQueryWrapper<LearningResource>()
                            .in(LearningResource::getPlanId, planIds));

            Map<Long, List<LearningResource>> resourceMap = allResources.stream()
                    .collect(Collectors.groupingBy(LearningResource::getPlanId));

            for (LearningPlan plan : plans) {
                List<LearningResource> resources = resourceMap.getOrDefault(plan.getId(), Collections.emptyList());
                if (resources.isEmpty()) {
                    plan.setDisplayStatus(0); // 待规划：没有资源
                } else if (resources.stream().anyMatch(r -> r.getStatus() == null || r.getStatus() < 2)) {
                    plan.setDisplayStatus(1); // 生成中：存在未完成的资源（status 0 或 1）
                } else {
                    plan.setDisplayStatus(4); // 已完成：所有资源 status >= 2
                }
            }
        }

        return PageResult.of(result.getTotal(), page, size, plans);
    }

    @Transactional
    public LearningPlan updatePlan(Long planId, Long userId, PlanCreateRequest request) {
        LearningPlan plan = getPlanById(planId, userId);
        plan.setTitle(request.getTitle());
        if (request.getLearningGoal() != null) {
            plan.setLearningGoal(toJson(request.getLearningGoal()));
        }
        if (request.getPlanConfig() != null) {
            plan.setPlanConfig(toJson(request.getPlanConfig()));
        }
        plan.setUpdatedAt(LocalDateTime.now());
        planMapper.updateById(plan);
        return plan;
    }

    @Transactional
    public void updatePlanStatus(Long planId, Integer status) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        plan.setStatus(status);
        plan.setUpdatedAt(LocalDateTime.now());
        planMapper.updateById(plan);
    }

    @Transactional
    public void updatePlanProgress(Long planId, Float progress) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        plan.setProgress(progress);
        plan.setUpdatedAt(LocalDateTime.now());
        planMapper.updateById(plan);
    }

    @Transactional
    public void deletePlan(Long planId, Long userId) {
        LearningPlan plan = getPlanById(planId, userId);

        // 级联删除子表关联数据
        LambdaQueryWrapper<LearningResource> resourceWrapper = new LambdaQueryWrapper<>();
        resourceWrapper.eq(LearningResource::getPlanId, planId);
        resourceMapper.delete(resourceWrapper);

        LambdaQueryWrapper<AiDialogue> dialogueWrapper = new LambdaQueryWrapper<>();
        dialogueWrapper.eq(AiDialogue::getPlanId, planId);
        dialogueMapper.delete(dialogueWrapper);

        LambdaQueryWrapper<QuizRecord> quizWrapper = new LambdaQueryWrapper<>();
        quizWrapper.eq(QuizRecord::getPlanId, planId);
        quizRecordMapper.delete(quizWrapper);

        LambdaQueryWrapper<LearningDuration> durationWrapper = new LambdaQueryWrapper<>();
        durationWrapper.eq(LearningDuration::getPlanId, planId);
        durationMapper.delete(durationWrapper);

        LambdaQueryWrapper<UserLearningProgress> progressWrapper = new LambdaQueryWrapper<>();
        progressWrapper.eq(UserLearningProgress::getPlanId, planId);
        progressMapper.delete(progressWrapper);

        LambdaQueryWrapper<ResourceGenerationTask> taskWrapper = new LambdaQueryWrapper<>();
        taskWrapper.eq(ResourceGenerationTask::getPlanId, planId);
        generationTaskMapper.delete(taskWrapper);

        // 软删除计划本身
        planMapper.deleteById(planId);
    }

    @Transactional
    public LearningPlan createPlanInternal(Long userId, String title, Object learningGoal, Object planConfig, Integer status) {
        LearningPlan plan = new LearningPlan();
        plan.setTitle(title);
        plan.setLearningGoal(toJson(learningGoal));
        plan.setPlanConfig(toJson(planConfig));
        plan.setUserId(userId);
        plan.setStatus(status != null ? status : 4);
        plan.setProgress(0.0f);
        plan.setCreatedAt(LocalDateTime.now());
        plan.setUpdatedAt(LocalDateTime.now());
        planMapper.insert(plan);
        return plan;
    }

    public LearningPlan getPlanByIdInternal(Long planId) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        return plan;
    }

    private String toJson(Object obj) {
        if (obj == null) return null;
        if (obj instanceof String) return (String) obj;
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            return obj.toString();
        }
    }
}
