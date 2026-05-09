package com.learning.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class TaskDispatchRequest {

    @NotNull(message = "计划ID不能为空")
    private Long planId;

    @NotNull(message = "资源ID不能为空")
    private Long resourceId;

    private String agentChain;
}
