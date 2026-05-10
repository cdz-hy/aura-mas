package com.learning.service;

import com.learning.entity.LearningPlan;
import com.learning.entity.ResourceGenerationTask;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mq.TaskProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskDispatchService {

    private final TaskProducer taskProducer;
    private final LearningResourceService learningResourceService;
    private final LearningPlanMapper planMapper;

    public ResourceGenerationTask dispatchTask(Long planId, Long resourceId, String agentChain) {
        return learningResourceService.dispatchGeneration(planId, resourceId, agentChain);
    }

    public void retryTask(Long taskId) {
        ResourceGenerationTask task = learningResourceService.getTaskById(taskId);
        task.setRetryCount(task.getRetryCount() + 1);
        task.setTaskStatus(0);
        LearningPlan plan = planMapper.selectById(task.getPlanId());
        Long userId = plan != null ? plan.getUserId() : null;
        taskProducer.sendGenerationTask(task, userId);
        log.info("Retrying task: {}, retryCount={}", taskId, task.getRetryCount());
    }

    public void updateTaskStatus(Long taskId, Integer status) {
        ResourceGenerationTask task = learningResourceService.getTaskById(taskId);
        task.setTaskStatus(status);
        if (status == 2 || status == 3) {
            task.setFinishedAt(java.time.LocalDateTime.now());
        }
        learningResourceService.updateTask(task);
    }
}
