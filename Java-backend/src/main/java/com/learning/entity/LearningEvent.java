package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_events")
public class LearningEvent {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String eventType;

    private String eventData;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
