package com.learning.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

public class KnowledgeTreeDtos {

    @Data
    public static class TreeResponse {
        private TreeDto tree;
        private List<NodeResponse> nodes;
    }

    @Data
    public static class TreeDto {
        private String id;
        private Long planId;
        private Long userId;
        private String title;
        private String field;
        private String currentProblem;
        private String learningBackground;
        private String currentNodeId;
        private String contextSummary;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
    }

    @Data
    public static class NodeResponse {
        private String id;
        private String treeId;
        private String parentId;
        private Long resourceId;
        private String title;
        private String summary;
        private String content;
        private String status;
        private Integer relevance;
        private Integer importance;
        private Integer relevanceScore;
        private Integer difficulty;
        private Integer depth;
        private Integer sortOrder;
        private List<String> prerequisiteIds;
        private Boolean isFundamental;
        private String fpRelation;
        private String fpReason;
        private Boolean collapsed;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
    }

    @Data
    public static class MessageResponse {
        private Long id;
        private String treeId;
        private String nodeId;
        private String role;
        private String content;
        private List<Object> nextActions;
        private List<Object> searchSources;
        private LocalDateTime createdAt;
    }

    @Data
    public static class CreateNodeRequest {
        private String id;
        private String treeId;
        private String parentId;
        private Long resourceId;
        private String title;
        private String summary;
        private String content;
        private String status;
        private Integer relevance;
        private Integer importance;
        private Integer relevanceScore;
        private Integer difficulty;
        private Integer depth;
        private Integer sortOrder;
        private List<String> prerequisiteIds;
        private Boolean isFundamental;
        private String fpRelation;
        private String fpReason;
        private Boolean collapsed;
    }

    @Data
    public static class UpdateNodeRequest {
        private String parentId;
        private String title;
        private String summary;
        private String content;
        private String status;
        private Integer relevance;
        private Integer importance;
        private Integer relevanceScore;
        private Integer difficulty;
        private Integer depth;
        private Integer sortOrder;
        private List<String> prerequisiteIds;
        private Boolean isFundamental;
        private String fpRelation;
        private String fpReason;
        private Boolean collapsed;
        private String currentNodeId;
    }

    @Data
    public static class AddMessageRequest {
        private String role;
        private String content;
        private List<Object> nextActions;
        private List<Object> searchSources;
    }

    @Data
    public static class BatchCreateNodesRequest {
        private List<CreateNodeRequest> nodes;
    }

    @Data
    public static class BatchCreateNodesResponse {
        private List<NodeResponse> nodes;
    }

    @Data
    public static class UpdateTreeRequest {
        private String title;
        private String field;
        private String currentProblem;
        private String learningBackground;
        private String contextSummary;
    }

    @Data
    public static class SyncTaskBreakdownRequest {
        private Long userId;
        private String title;
        private String description;
        private String learningBackground;
        private List<Object> modules;
    }
}
