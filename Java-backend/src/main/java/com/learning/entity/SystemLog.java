package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("system_log")
public class SystemLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String operationType;

    private String resourceId;

    private String userIp;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
