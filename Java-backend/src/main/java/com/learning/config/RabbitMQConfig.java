package com.learning.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.CachingConnectionFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Configuration
public class RabbitMQConfig {

    public static final String EXCHANGE_NAME = "ai.exchange";
    public static final String QUEUE_GENERATION = "ai.resource.generation";
    public static final String QUEUE_RESULT = "ai.resource.result";
    public static final String ROUTING_KEY_GENERATION = "ai.resource.generation";
    public static final String ROUTING_KEY_RESULT = "ai.resource.result";

    @Value("${spring.rabbitmq.host:localhost}")
    private String host;

    @Value("${spring.rabbitmq.port:5672}")
    private int port;

    @Value("${spring.rabbitmq.username:guest}")
    private String username;

    @Value("${spring.rabbitmq.password:guest}")
    private String password;

    @Value("${spring.rabbitmq.virtual-host:/}")
    private String virtualHost;

    @Bean
    public ConnectionFactory rabbitConnectionFactory() {
        CachingConnectionFactory factory = new CachingConnectionFactory();
        factory.setHost(host);
        factory.setPort(port);
        factory.setUsername(username);
        factory.setPassword(password);
        factory.setVirtualHost(virtualHost);
        factory.setConnectionTimeout(3000);
        return factory;
    }

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

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        return template;
    }
}
