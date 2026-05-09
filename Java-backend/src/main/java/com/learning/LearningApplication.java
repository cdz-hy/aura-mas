package com.learning;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.amqp.RabbitAutoConfiguration;

@SpringBootApplication(exclude = {RabbitAutoConfiguration.class})
@MapperScan("com.learning.mapper")
public class LearningApplication {

    public static void main(String[] args) {
        SpringApplication.run(LearningApplication.class, args);
    }
}
