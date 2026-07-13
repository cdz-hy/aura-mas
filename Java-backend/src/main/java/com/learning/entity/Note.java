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

    private String tags;

    private Integer isPinned;

    /** excerpt | quick | question — null for legacy notes */
    private String noteType;

    /** pending | organizing | organized | error — null for legacy notes */
    private String organizeStatus;

    /** plan | resource | knowledge_tree | tutor — null when no automatic source */
    private String sourceType;

    private Long sourceId;

    private String sourceTitle;

    private String sourceRoute;

    private String excerpt;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
