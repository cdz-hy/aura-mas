package com.learning.service;

import com.learning.entity.LearningPlan;
import com.learning.entity.LearningResource;
import com.learning.entity.ResourceGenerationTask;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mq.TaskProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskDispatchService {

    private final TaskProducer taskProducer;
    private final LearningResourceService learningResourceService;
    private final LearningPlanMapper planMapper;
    private final TaskSseService taskSseService;

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
            task.setFinishedAt(LocalDateTime.now());
        }
        learningResourceService.updateTask(task);

        // 同步更新资源状态
        learningResourceService.updateResourceStatus(task.getResourceId(), status);

        // SSE 推送任务完成通知到前端（替代原来的 MQ 结果队列）
        if (status == 2 || status == 3) {
            LearningPlan plan = planMapper.selectById(task.getPlanId());
            if (plan != null) {
                LearningResource resource = learningResourceService.getResourceById(task.getResourceId());
                String moduleData = resource != null ? resource.getModuleData() : null;
                taskSseService.sendTaskUpdate(plan.getUserId(), taskId, status, moduleData);
            }
        }
    }
}
