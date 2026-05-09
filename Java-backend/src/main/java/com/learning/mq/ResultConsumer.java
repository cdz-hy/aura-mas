package com.learning.mq;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.learning.config.RabbitMQConfig;
import com.learning.entity.LearningResource;
import com.learning.entity.ResourceGenerationTask;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.ResourceGenerationTaskMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class ResultConsumer {

    private final ResourceGenerationTaskMapper taskMapper;
    private final LearningResourceMapper resourceMapper;

    @RabbitListener(queues = RabbitMQConfig.QUEUE_RESULT)
    public void handleGenerationResult(Map<String, Object> message) {
        log.info("Received generation result: {}", message);

        Long taskId = Long.valueOf(message.get("taskId").toString());
        Integer status = Integer.valueOf(message.get("status").toString());
        String storagePath = (String) message.get("storagePath");
        String moduleData = (String) message.get("moduleData");

        ResourceGenerationTask task = taskMapper.selectById(taskId);
        if (task == null) {
            log.warn("Task not found: {}", taskId);
            return;
        }

        task.setTaskStatus(status);
        task.setFinishedAt(LocalDateTime.now());
        taskMapper.updateById(task);

        LearningResource resource = resourceMapper.selectById(task.getResourceId());
        if (resource != null) {
            LambdaUpdateWrapper<LearningResource> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.eq(LearningResource::getId, resource.getId());

            if (moduleData != null) {
                updateWrapper.set(LearningResource::getModuleData, moduleData);
            }
            if (storagePath != null) {
                updateWrapper.set(LearningResource::getStoragePath, storagePath);
            }
            updateWrapper.set(LearningResource::getStatus, status);
            resourceMapper.update(null, updateWrapper);

            log.info("Updated resource: resourceId={}, status={}", resource.getId(), status);
        }
    }
}
