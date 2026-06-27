package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.learning.config.ModuleDataDeserializer;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_resource")
public class LearningResource {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long planId;

    private Long parentId;

    private Integer moduleOrder;

    private String moduleType;

    @JsonDeserialize(using = ModuleDataDeserializer.class)
    private String moduleData;

    private Integer status;

    private String storagePath;

    private String generatedByAgent;

    private Integer version;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
