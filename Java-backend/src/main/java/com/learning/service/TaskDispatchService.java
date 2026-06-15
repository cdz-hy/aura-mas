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

    public ResourceGenerationTask createInternalTask(Long planId, Long resourceId, String agentChain) {
        return learningResourceService.createGenerationTask(planId, resourceId, agentChain);
    }

    private static final int MAX_RETRY_COUNT = 3;

    public void retryTask(Long taskId) {
        ResourceGenerationTask task = learningResourceService.getTaskById(taskId);
        if (task.getRetryCount() >= MAX_RETRY_COUNT) {
            throw new com.learning.exception.BusinessException(
                    com.learning.common.ErrorCode.BAD_REQUEST.getCode(), "已达到最大重试次数（" + MAX_RETRY_COUNT + "次）");
        }

        task.setRetryCount(task.getRetryCount() + 1);
        task.setTaskStatus(1);
        task.setFinishedAt(null);
        learningResourceService.updateTask(task);

        learningResourceService.updateResourceStatus(task.getResourceId(), 1);

        LearningPlan plan = planMapper.selectById(task.getPlanId());
        Long userId = plan != null ? plan.getUserId() : null;
        taskProducer.sendGenerationTask(task, userId);
        log.info("Retrying task: {}, retryCount={}", taskId, task.getRetryCount());
    }

    @org.springframework.transaction.annotation.Transactional
    public void completeTask(Long taskId, String moduleData) {
        ResourceGenerationTask task = learningResourceService.getTaskById(taskId);
        Long planId = task.getPlanId();
        Long resourceId = task.getResourceId();

        // 先持久化资源内容（确保内容落库成功）
        learningResourceService.updateContent(resourceId, moduleData, 2);

        // 再更新任务状态为完成
        task.setTaskStatus(2);
        task.setFinishedAt(LocalDateTime.now());
        learningResourceService.updateTask(task);

        // 事务提交后再推送 SSE，避免事务回滚时前端收到虚假完成通知
        org.springframework.transaction.support.TransactionSynchronizationManager.registerSynchronization(
                new org.springframework.transaction.support.TransactionSynchronization() {
                    @Override
                    public void afterCommit() {
                        LearningPlan plan = planMapper.selectById(planId);
                        if (plan != null) {
                            taskSseService.sendTaskUpdate(plan.getUserId(), taskId, 2, moduleData);
                        }
                    }
                });
    }

    public void updateTaskStatus(Long taskId, Integer status) {
        updateTaskStatus(taskId, status, true);
    }

    public void updateTaskStatus(Long taskId, Integer status, boolean updateResourceStatus) {
        ResourceGenerationTask task = learningResourceService.getTaskById(taskId);

        // 任务失败时自动重试（不标记为失败，直接重新派发）
        if (status == 3 && task.getRetryCount() < MAX_RETRY_COUNT) {
            log.info("任务 {} 失败，自动重试 (retryCount={})", taskId, task.getRetryCount());
            retryTask(taskId);
            return;
        }

        task.setTaskStatus(status);
        if (status == 2 || status == 3) {
            task.setFinishedAt(LocalDateTime.now());
        }
        learningResourceService.updateTask(task);

        // 同步更新资源状态
        if (updateResourceStatus) {
            learningResourceService.updateResourceStatus(task.getResourceId(), status);
        }

        // SSE 推送任务完成通知到前端（替代原来的 MQ 结果队列）
        if (status == 2 || status == 3) {
            LearningPlan plan = planMapper.selectById(task.getPlanId());
            if (plan != null) {
                LearningResource resource = updateResourceStatus
                        ? learningResourceService.findResourceById(task.getResourceId())
                        : null;
                String moduleData = resource != null ? resource.getModuleData() : null;
                taskSseService.sendTaskUpdate(plan.getUserId(), taskId, status, moduleData);
            }
        }
    }
}
