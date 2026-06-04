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

    private String selectedText;

    private String positionInfo;
}
