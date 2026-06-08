package com.learning.mq;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.config.RabbitMQConfig;
import com.learning.entity.ResourceGenerationTask;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class TaskProducer {

    private final RabbitTemplate rabbitTemplate;
    private final ObjectMapper objectMapper;

    public void sendGenerationTask(ResourceGenerationTask task, Long userId) {
        Map<String, Object> message = new HashMap<>();
        message.put("taskId", task.getId());
        message.put("planId", task.getPlanId());
        message.put("resourceId", task.getResourceId());
        message.put("agentChain", task.getAgentChain());
        if (userId != null) {
            message.put("userId", userId);
        }

        try {
            String payload = objectMapper.writeValueAsString(message);
            rabbitTemplate.convertAndSend(
                    RabbitMQConfig.EXCHANGE_NAME,
                    RabbitMQConfig.ROUTING_KEY_GENERATION,
                    payload,
                    msg -> {
                        msg.getMessageProperties().setContentType(MessageProperties.CONTENT_TYPE_JSON);
                        return msg;
                    });
            log.info("Sent generation task: taskId={}, planId={}, resourceId={}, userId={}",
                    task.getId(), task.getPlanId(), task.getResourceId(), userId);
        } catch (Exception e) {
            log.warn("RabbitMQ not available, task saved to DB only: taskId={}, error={}",
                    task.getId(), e.getMessage());
        }
    }
}
