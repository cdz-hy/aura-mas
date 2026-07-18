package com.learning.dto;

import lombok.Data;

@Data
public class KnowledgeGraphUpdateReq {
    private String domainName;
    private Object graphData;
}
