package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user_profile")
public class UserProfile {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private Integer version;

    private Integer isCurrent;

    private String age;

    private String gender;

    private String domain;

    private String learningBehavior;

    private String updateReason;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
