package com.learning.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Data
public class NoteCreateRequest {

    @NotBlank(message = "笔记名称不能为空")
    private String noteName;

    @NotBlank(message = "内容不能为空")
    private String content;

    private List<String> tags;

    private Integer isPinned;
}
