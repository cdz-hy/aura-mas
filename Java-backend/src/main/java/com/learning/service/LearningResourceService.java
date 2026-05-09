package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.ErrorCode;
import com.learning.entity.LearningResource;
import com.learning.entity.ResourceGenerationTask;
import com.learning.exception.BusinessException;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.ResourceGenerationTaskMapper;
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

    @Transactional
    public LearningResource createResource(LearningResource resource) {
        resource.setCreatedAt(LocalDateTime.now());
        resource.setUpdatedAt(LocalDateTime.now());
        resource.setStatus(0);
        resource.setVersion(1);
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

        taskProducer.sendGenerationTask(task);

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
}
