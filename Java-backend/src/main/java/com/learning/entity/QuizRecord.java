package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("quiz_record")
public class QuizRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long resourceId;

    private Long userId;

    private Long planId;

    private String questionType;

    private Integer difficulty;

    private String correctAnswer;

    private String userAnswer;

    private Integer isCorrect;

    private LocalDateTime answerTime;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
