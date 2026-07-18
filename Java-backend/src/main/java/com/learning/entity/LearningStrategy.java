package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_strategies")
public class LearningStrategy {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String strategyType;

    private String title;

    private String description;

    private String strategyData;

    private String status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    private LocalDateTime expiresAt;

    private LocalDateTime acceptedAt;
}
