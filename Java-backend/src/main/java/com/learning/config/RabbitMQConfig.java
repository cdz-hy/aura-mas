package com.learning.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.annotation.EnableRabbit;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import lombok.extern.slf4j.Slf4j;

/**
 * RabbitMQ 配置
 * ConnectionFactory / RabbitTemplate / MessageConverter 由 Spring Boot 自动配置
 * 此处仅定义自定义的 Exchange、Queue、Binding
 */
@Slf4j
@Configuration
@EnableRabbit
public class RabbitMQConfig {

    public static final String EXCHANGE_NAME = "ai.exchange";
    public static final String QUEUE_GENERATION = "ai.resource.generation";
    public static final String QUEUE_RESULT = "ai.resource.result";
    public static final String ROUTING_KEY_GENERATION = "ai.resource.generation";
    public static final String ROUTING_KEY_RESULT = "ai.resource.result";

    @Bean
    public DirectExchange aiExchange() {
        return new DirectExchange(EXCHANGE_NAME);
    }

    @Bean
    public Queue generationQueue() {
        return QueueBuilder.durable(QUEUE_GENERATION).build();
    }

    @Bean
    public Queue resultQueue() {
        return QueueBuilder.durable(QUEUE_RESULT).build();
    }

    @Bean
    public Binding generationBinding(Queue generationQueue, DirectExchange aiExchange) {
        return BindingBuilder.bind(generationQueue).to(aiExchange).with(ROUTING_KEY_GENERATION);
    }

    @Bean
    public Binding resultBinding(Queue resultQueue, DirectExchange aiExchange) {
        return BindingBuilder.bind(resultQueue).to(aiExchange).with(ROUTING_KEY_RESULT);
    }
}
