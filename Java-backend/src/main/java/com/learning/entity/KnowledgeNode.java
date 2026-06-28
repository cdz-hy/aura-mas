package com.learning.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("knowledge_node")
public class KnowledgeNode {

    @TableId(type = IdType.INPUT)
    private String id;

    private String treeId;

    private String parentId;

    private Long resourceId;

    private String title;

    private String summary;

    private String content;

    private String status;

    private Integer relevance;

    private Integer importance;

    private Integer relevanceScore;

    private Integer difficulty;

    private Integer depth;

    private Integer sortOrder;

    private String prerequisiteIds;

    private Boolean isFundamental;

    private String fpRelation;

    private String fpReason;

    private Boolean collapsed;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
