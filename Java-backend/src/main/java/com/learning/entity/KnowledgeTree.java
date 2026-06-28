package com.learning.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("knowledge_tree")
public class KnowledgeTree {

    @TableId(type = IdType.INPUT)
    private String id;

    private Long planId;

    private Long userId;

    private String title;

    private String field;

    private String currentProblem;

    private String learningBackground;

    private String currentNodeId;

    private String contextSummary;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
