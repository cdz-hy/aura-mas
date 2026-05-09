package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_duration")
public class LearningDuration {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private Long planId;

    private Long resourceId;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private Integer durationSeconds;

    private String terminalType;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
