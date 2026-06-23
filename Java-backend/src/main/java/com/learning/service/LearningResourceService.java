package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.ErrorCode;
import com.learning.entity.AiDialogue;
import com.learning.entity.LearningDuration;
import com.learning.entity.LearningPlan;
import com.learning.entity.LearningResource;
import com.learning.entity.NoteResourceRel;
import com.learning.entity.QuizRecord;
import com.learning.entity.ResourceGenerationTask;
import com.learning.entity.UserLearningProgress;
import com.learning.exception.BusinessException;
import com.learning.mapper.AiDialogueMapper;
import com.learning.mapper.LearningDurationMapper;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.NoteResourceRelMapper;
import com.learning.mapper.QuizRecordMapper;
import com.learning.mapper.ResourceGenerationTaskMapper;
import com.learning.mapper.UserLearningProgressMapper;
import com.learning.mq.TaskProducer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class LearningResourceService {

    private final LearningResourceMapper resourceMapper;
    private final ResourceGenerationTaskMapper taskMapper;
    private final TaskProducer taskProducer;
    private final LearningPlanMapper planMapper;
    private final AiDialogueMapper dialogueMapper;
    private final QuizRecordMapper quizRecordMapper;
    private final LearningDurationMapper durationMapper;
    private final UserLearningProgressMapper progressMapper;
    private final NoteResourceRelMapper noteResourceRelMapper;

    public List<LearningResource> getResourcesByPlanId(Long planId) {
        return resourceMapper.selectList(
                new LambdaQueryWrapper<LearningResource>()
                        .eq(LearningResource::getPlanId, planId)
                        .orderByAsc(LearningResource::getModuleOrder));
    }

    public LearningResource getResourceById(Long resourceId) {
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource == null) {
            throw new BusinessException(ErrorCode.RESOURCE_NOT_FOUND);
        }
        return resource;
    }

    public LearningResource findResourceById(Long resourceId) {
        return resourceMapper.selectById(resourceId);
    }

    @Transactional
    public LearningResource createResource(LearningResource resource) {
        resource.setCreatedAt(LocalDateTime.now());
        resource.setUpdatedAt(LocalDateTime.now());
        if (resource.getStatus() == null) {
            resource.setStatus(0);
        }
        if (resource.getVersion() == null) {
            resource.setVersion(1);
        }
        resourceMapper.insert(resource);
        return resource;
    }

    @Transactional
    public ResourceGenerationTask dispatchGeneration(Long planId, Long resourceId, String agentChain) {
        ResourceGenerationTask task = new ResourceGenerationTask();
        task.setPlanId(planId);
        task.setResourceId(resourceId);
        task.setTaskStatus(0);
        task.setAgentChain(agentChain);
        task.setRetryCount(0);
        task.setCreatedAt(LocalDateTime.now());
        taskMapper.insert(task);

        // 获取 userId 包含在 MQ 消息中，供 Python 消费者使用
        LearningPlan plan = planMapper.selectById(planId);
        Long userId = plan != null ? plan.getUserId() : null;
        taskProducer.sendGenerationTask(task, userId);

        task.setTaskStatus(1);
        taskMapper.updateById(task);

        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource != null) {
            resource.setStatus(1);
            resource.setUpdatedAt(LocalDateTime.now());
            resourceMapper.updateById(resource);
        }

        return task;
    }

    @Transactional
    public ResourceGenerationTask createGenerationTask(Long planId, Long resourceId, String agentChain) {
        ResourceGenerationTask task = new ResourceGenerationTask();
        task.setPlanId(planId);
        task.setResourceId(resourceId);
        task.setTaskStatus(1);
        task.setAgentChain(agentChain);
        task.setRetryCount(0);
        task.setCreatedAt(LocalDateTime.now());
        taskMapper.insert(task);
        return task;
    }

    public ResourceGenerationTask getTaskById(Long taskId) {
        ResourceGenerationTask task = taskMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(ErrorCode.TASK_NOT_FOUND);
        }
        return task;
    }

    @Transactional
    public void updateResourceStatus(Long resourceId, Integer status) {
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource != null) {
            resource.setStatus(status);
            resource.setUpdatedAt(LocalDateTime.now());
            resourceMapper.updateById(resource);
        }
    }

    @Transactional
    public List<LearningResource> bulkCreate(List<LearningResource> resources) {
        for (LearningResource resource : resources) {
            resource.setCreatedAt(LocalDateTime.now());
            resource.setUpdatedAt(LocalDateTime.now());
            if (resource.getStatus() == null) resource.setStatus(0);
            if (resource.getVersion() == null) resource.setVersion(1);
            resourceMapper.insert(resource);
        }
        return resources;
    }

    @Transactional
    public void updateContent(Long resourceId, String moduleData, Integer status) {
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource != null) {
            if (moduleData != null) resource.setModuleData(moduleData);
            if (status != null) resource.setStatus(status);
            resource.setUpdatedAt(LocalDateTime.now());
            resourceMapper.updateById(resource);
        }
    }

    public List<LearningResource> getResourcesByModule(Long planId, Integer moduleOrder) {
        return resourceMapper.selectList(
                new LambdaQueryWrapper<LearningResource>()
                        .eq(LearningResource::getPlanId, planId)
                        .eq(LearningResource::getModuleOrder, moduleOrder)
                        .orderByAsc(LearningResource::getId));
    }

    @Transactional
    public void updateTask(ResourceGenerationTask task) {
        taskMapper.updateById(task);
    }

    @Transactional
    public void deleteResource(Long resourceId, Long userId) {
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource == null) {
            throw new BusinessException(ErrorCode.RESOURCE_NOT_FOUND);
        }
        // 权限校验：必须为资源所属计划的拥有者
        LearningPlan plan = planMapper.selectById(resource.getPlanId());
        if (plan == null || !plan.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }

        // 级联清理子表关联数据
        LambdaQueryWrapper<ResourceGenerationTask> taskWrapper = new LambdaQueryWrapper<>();
        taskWrapper.eq(ResourceGenerationTask::getResourceId, resourceId);
        taskMapper.delete(taskWrapper);

        LambdaQueryWrapper<UserLearningProgress> progressWrapper = new LambdaQueryWrapper<>();
        progressWrapper.eq(UserLearningProgress::getResourceId, resourceId);
        progressMapper.delete(progressWrapper);

        LambdaQueryWrapper<LearningDuration> durationWrapper = new LambdaQueryWrapper<>();
        durationWrapper.eq(LearningDuration::getResourceId, resourceId);
        durationMapper.delete(durationWrapper);

        LambdaQueryWrapper<NoteResourceRel> noteRelWrapper = new LambdaQueryWrapper<>();
        noteRelWrapper.eq(NoteResourceRel::getResourceId, resourceId);
        noteResourceRelMapper.delete(noteRelWrapper);

        LambdaQueryWrapper<QuizRecord> quizWrapper = new LambdaQueryWrapper<>();
        quizWrapper.eq(QuizRecord::getResourceId, resourceId);
        quizRecordMapper.delete(quizWrapper);

        LambdaQueryWrapper<AiDialogue> dialogueWrapper = new LambdaQueryWrapper<>();
        dialogueWrapper.eq(AiDialogue::getResourceId, resourceId);
        dialogueMapper.delete(dialogueWrapper);

        // 软删除资源主体
        resourceMapper.deleteById(resourceId);
    }
}
