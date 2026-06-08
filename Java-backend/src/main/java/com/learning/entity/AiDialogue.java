package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_dialogue")
public class AiDialogue {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String sessionId;

    private Long planId;

    private Long resourceId;

    private String conversationText;

    private String conversationContext;

    private LocalDateTime dialogueTime;

    private String dialogueType;

    private String intentType;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
