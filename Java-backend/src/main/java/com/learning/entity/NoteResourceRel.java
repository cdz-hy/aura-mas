package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

@Data
@TableName("note_resource_rel")
public class NoteResourceRel {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long noteId;

    private Long resourceId;

    @TableField(exist = false)
    private String selectedText;

    @TableField(exist = false)
    private String positionInfo;

    @TableField(exist = false)
    private Long planId;

    @TableField(exist = false)
    private String moduleName;

    @TableField(exist = false)
    private String resourceTitle;
}
