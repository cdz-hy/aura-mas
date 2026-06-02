package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("daily_study_time")
public class DailyStudyTime {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private LocalDate studyDate;

    private Integer durationSeconds;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
