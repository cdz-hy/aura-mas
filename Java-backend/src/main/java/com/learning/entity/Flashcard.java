package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("flashcard")
public class Flashcard {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long noteId;

    private Long userId;

    private String question;

    private String answer;

    private Integer difficulty;

    private Double easeFactor;

    private Integer reviewInterval;

    private Integer reviewCount;

    private LocalDateTime nextReviewAt;

    private LocalDateTime createdAt;
}
