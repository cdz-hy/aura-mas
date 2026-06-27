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
                } else if (resources.stream().anyMatch(r -> r.getStatus() == null || r.getStatus() < 2 || r.getStatus() == 3)) {
                    plan.setDisplayStatus(1); // 生成中：存在未完成或失败的资源（status 0、1 或 3）
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
    public void updatePlanConfig(Long planId, Object newConfig) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        plan.setPlanConfig(toJson(newConfig));
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

    /**
     * 会话级 learning_goal 增量更新（保留演进历史）
     * 数据结构：
     * {
     *   "sessions": {
     *     "<sessionId>": {
     *       "current": "...",
     *       "history": [{goal, action, reasoning, timestamp}, ...],
     *       "updated_at": "..."
     *     }
     *   },
     *   "initial": "..."  // 向后兼容：原始计划创建时的字符串目标
     * }
     */
    @Transactional
    public synchronized void upsertSessionLearningGoal(Long planId, String sessionId, String goal,
                                                       String action, String reasoning) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        Map<String, Object> goalMap = parseGoalJson(plan.getLearningGoal());

        Map<String, Object> sessions = (Map<String, Object>) goalMap.get("sessions");
        if (sessions == null) {
            sessions = new LinkedHashMap<>();
            goalMap.put("sessions", sessions);
        }

        Map<String, Object> sessionEntry = (Map<String, Object>) sessions.get(sessionId);
        if (sessionEntry == null) {
            sessionEntry = new LinkedHashMap<>();
            sessionEntry.put("current", "");
            sessionEntry.put("history", new ArrayList<>());
            sessions.put(sessionId, sessionEntry);
        }

        String prevGoal = (String) sessionEntry.getOrDefault("current", "");
        if (goal.equals(prevGoal)) {
            return; // 无变化，跳过写入
        }

        String now = LocalDateTime.now().toString();
        sessionEntry.put("current", goal);
        sessionEntry.put("updated_at", now);

        List<Map<String, Object>> history = (List<Map<String, Object>>) sessionEntry.get("history");
        if (history == null) {
            history = new ArrayList<>();
            sessionEntry.put("history", history);
        }
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("goal", goal);
        entry.put("action", action);
        entry.put("reasoning", reasoning);
        entry.put("timestamp", now);
        history.add(entry);

        plan.setLearningGoal(toJson(goalMap));
        plan.setUpdatedAt(LocalDateTime.now());
        planMapper.updateById(plan);
    }

    /**
     * 解析 learning_goal JSON 字段。
     * 兼容三种历史格式：
     * 1. null/空 → 返回空 Map
     * 2. 普通字符串（旧格式，计划创建时存的简单字符串）→ 包装为 {"initial": "<string>"}
     * 3. JSON 对象（新格式）→ 直接返回
     */
    private Map<String, Object> parseGoalJson(String raw) {
        if (raw == null || raw.isEmpty()) {
            return new LinkedHashMap<>();
        }
        try {
            Object parsed = objectMapper.readValue(raw, Object.class);
            if (parsed instanceof Map) {
                return (Map<String, Object>) parsed;
            }
            if (parsed instanceof String) {
                Map<String, Object> wrapped = new LinkedHashMap<>();
                wrapped.put("initial", parsed);
                return wrapped;
            }
        } catch (Exception e) {
            // 解析失败时把原始字符串当作 initial 兜底
            Map<String, Object> wrapped = new LinkedHashMap<>();
            wrapped.put("initial", raw);
            return wrapped;
        }
        return new LinkedHashMap<>();
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
