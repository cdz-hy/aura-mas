package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.learning.typehandler.JsonStringTypeHandler;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName(value = "resource_generation_task", autoResultMap = true)
public class ResourceGenerationTask {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long planId;

    private Long resourceId;

    private Integer taskStatus;

    @TableField(typeHandler = JsonStringTypeHandler.class)
    private String agentChain;

    private Integer retryCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    private LocalDateTime finishedAt;
}
