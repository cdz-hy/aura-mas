package com.learning.dto;

import lombok.Builder;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
public class MenuNode {
    private String code;
    private String name;
    private String path;
    private String icon;
    private String type;

    @Builder.Default
    private List<MenuNode> children = new ArrayList<>();
}
