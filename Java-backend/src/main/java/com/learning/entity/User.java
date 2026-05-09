package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user")
public class User {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String loginName;

    private String password;

    private String nickname;

    private String email;

    private String avatarUrl;

    private String role;

    private Integer status;

    private LocalDateTime lastLoginTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
