package com.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("tree_message")
public class TreeMessage {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String treeId;

    private String nodeId;

    private String role;

    private String content;

    private String nextActions;

    private String searchSources;

    private LocalDateTime createdAt;
}
