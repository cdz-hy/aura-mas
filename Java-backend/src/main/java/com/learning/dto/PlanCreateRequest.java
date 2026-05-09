package com.learning.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class PlanCreateRequest {

    @NotBlank(message = "标题不能为空")
    private String title;

    private Object learningGoal;

    private Object planConfig;
}
