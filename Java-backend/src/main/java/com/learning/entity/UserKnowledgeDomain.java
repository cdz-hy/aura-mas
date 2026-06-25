package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName(value = "user_knowledge_domain", autoResultMap = true)
public class UserKnowledgeDomain {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String domainName;

    // MyBatis-Plus 需要专门的 TypeHandler 来处理 JSON，否则会报错或按 String 处理
    // 因为这里用 JSON 类型，需要在类上加 autoResultMap = true，并在字段上配置 typeHandler
    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private Object graphData;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    @TableLogic
    private Integer isDeleted;
}
