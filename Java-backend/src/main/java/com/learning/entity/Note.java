package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("note")
public class Note {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String noteName;

    private String content;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
