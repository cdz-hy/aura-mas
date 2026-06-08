package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("knowledge_base")
public class KnowledgeBase {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String docName;

    private String filePath;

    private Long fileSize;

    private Integer chunkCount;

    private Integer parseStatus;

    private String collectionName;

    private String mineruTaskId;

    private Long uploadUserId;

    private LocalDateTime uploadTime;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
