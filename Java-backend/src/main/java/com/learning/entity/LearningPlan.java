package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_plan")
public class LearningPlan {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String title;

    private String learningGoal;

    private String planConfig;

    private Long userId;

    private Integer status;

    private Float progress;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
