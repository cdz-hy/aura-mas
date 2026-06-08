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
    public static final String ROUTING_KEY_GENERATION = "ai.resource.generation";

    // 死信队列配置
    public static final String DLX_EXCHANGE_NAME = "ai.dlx.exchange";
    public static final String DLX_QUEUE = "ai.resource.generation.dlx";
    public static final String DLX_ROUTING_KEY = "ai.resource.generation.dlx";

    /** 最大投递次数（超过后进入死信队列） */
    public static final int MAX_DELIVERY_COUNT = 3;

    @Bean
    public DirectExchange aiExchange() {
        return new DirectExchange(EXCHANGE_NAME);
    }

    @Bean
    public DirectExchange dlxExchange() {
        return new DirectExchange(DLX_EXCHANGE_NAME);
    }

    @Bean
    public Queue generationQueue() {
        return QueueBuilder.durable(QUEUE_GENERATION)
                .withArgument("x-dead-letter-exchange", DLX_EXCHANGE_NAME)
                .withArgument("x-dead-letter-routing-key", DLX_ROUTING_KEY)
                .build();
    }

    @Bean
    public Queue dlxQueue() {
        return QueueBuilder.durable(DLX_QUEUE).build();
    }

    @Bean
    public Binding generationBinding(Queue generationQueue, DirectExchange aiExchange) {
        return BindingBuilder.bind(generationQueue).to(aiExchange).with(ROUTING_KEY_GENERATION);
    }

    @Bean
    public Binding dlxBinding(Queue dlxQueue, DirectExchange dlxExchange) {
        return BindingBuilder.bind(dlxQueue).to(dlxExchange).with(DLX_ROUTING_KEY);
    }
}
