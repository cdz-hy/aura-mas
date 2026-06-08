package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("menu")
public class Menu {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String code;

    private String name;

    private String path;

    private String icon;

    private Long parentId;

    private String type;

    private Integer sortOrder;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
