package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("resource_generation_task")
public class ResourceGenerationTask {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long planId;

    private Long resourceId;

    private Integer taskStatus;

    private String agentChain;

    private Integer retryCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    private LocalDateTime finishedAt;
}
