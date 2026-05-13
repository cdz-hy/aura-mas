package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_token_usage")
public class AiTokenUsage {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private Long taskId;

    private String scene;

    private String modelName;

    private Integer inputTokens;

    private Integer outputTokens;

    @TableField(exist = false)
    private Integer totalTokens;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
