package com.learning.mq;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.config.RabbitMQConfig;
import com.learning.entity.ResourceGenerationTask;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class TaskProducerTest {

    @Test
    void sendsGenerationTaskAsJsonTextForPythonConsumer() throws Exception {
        RabbitTemplate rabbitTemplate = mock(RabbitTemplate.class);
        ObjectMapper objectMapper = new ObjectMapper();
        TaskProducer producer = new TaskProducer(rabbitTemplate, objectMapper);

        ResourceGenerationTask task = new ResourceGenerationTask();
        task.setId(20L);
        task.setPlanId(12L);
        task.setResourceId(0L);
        task.setAgentChain("text");

        producer.sendGenerationTask(task, 1L);

        ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
        verify(rabbitTemplate).convertAndSend(
                org.mockito.ArgumentMatchers.eq(RabbitMQConfig.EXCHANGE_NAME),
                org.mockito.ArgumentMatchers.eq(RabbitMQConfig.ROUTING_KEY_GENERATION),
                payloadCaptor.capture(),
                org.mockito.ArgumentMatchers.any(MessagePostProcessor.class)
        );

        String payload = (String) payloadCaptor.getValue();
        JsonNode json = objectMapper.readTree(payload);
        assertEquals(20L, json.get("taskId").asLong());
        assertEquals(12L, json.get("planId").asLong());
        assertEquals(0L, json.get("resourceId").asLong());
        assertEquals(1L, json.get("userId").asLong());
        assertEquals("text", json.get("agentChain").asText());
    }
}
