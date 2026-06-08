package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.common.ErrorCode;
import com.learning.dto.KnowledgeTreeDtos;
import com.learning.entity.KnowledgeNode;
import com.learning.entity.KnowledgeTree;
import com.learning.entity.LearningPlan;
import com.learning.entity.LearningResource;
import com.learning.entity.TreeMessage;
import com.learning.exception.BusinessException;
import com.learning.mapper.KnowledgeNodeMapper;
import com.learning.mapper.KnowledgeTreeMapper;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.TreeMessageMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class KnowledgeTreeService {

    private static final String STATUS_PENDING = "pending";
    private static final Set<String> MESSAGE_ROLES = Set.of("USER", "ASSISTANT", "SYSTEM");

    private final KnowledgeTreeMapper treeMapper;
    private final KnowledgeNodeMapper nodeMapper;
    private final TreeMessageMapper messageMapper;
    private final LearningPlanMapper planMapper;
    private final LearningResourceMapper resourceMapper;
    private final ObjectMapper objectMapper;

    @Transactional
    public KnowledgeTreeDtos.TreeResponse createOrGetByPlan(Long planId, Long userId) {
        LearningPlan plan = requireOwnedPlan(planId, userId);
        KnowledgeTree existing = treeMapper.selectOne(new LambdaQueryWrapper<KnowledgeTree>()
                .eq(KnowledgeTree::getPlanId, planId)
                .eq(KnowledgeTree::getUserId, userId));
        if (existing != null) {
            return toTreeResponse(existing, loadNodes(existing.getId()));
        }

        LocalDateTime now = LocalDateTime.now();
        KnowledgeTree tree = new KnowledgeTree();
        tree.setId(nextId("tree"));
        tree.setPlanId(planId);
        tree.setUserId(userId);
        tree.setTitle(plan.getTitle());
        tree.setField("");
        tree.setCurrentProblem("");
        tree.setLearningBackground("");
        tree.setContextSummary("");
        tree.setCreatedAt(now);
        tree.setUpdatedAt(now);

        KnowledgeNode root = new KnowledgeNode();
        root.setId(nextId("node"));
        root.setTreeId(tree.getId());
        root.setTitle(plan.getTitle());
        root.setSummary("学习计划总览");
        root.setContent(plan.getLearningGoal());
        root.setStatus("active");
        root.setRelevance(0);
        root.setImportance(3);
        root.setRelevanceScore(3);
        root.setDifficulty(2);
        root.setDepth(0);
        root.setSortOrder(0);
        root.setPrerequisiteIds(null);
        root.setIsFundamental(false);
        root.setFpRelation("");
        root.setCollapsed(false);
        root.setCreatedAt(now);
        root.setUpdatedAt(now);

        tree.setCurrentNodeId(root.getId());
        treeMapper.insert(tree);
        nodeMapper.insert(root);

        List<KnowledgeNode> nodes = new ArrayList<>();
        nodes.add(root);
        List<ModuleSeed> moduleSeeds = moduleSeedsFromLearningGoal(plan.getLearningGoal());
        if (moduleSeeds.isEmpty()) {
            moduleSeeds = moduleSeedsFromResources(planId);
        }
        if (moduleSeeds.isEmpty()) {
            moduleSeeds = List.of(new ModuleSeed("学习总览", "从整体目标开始梳理学习路径", null, null));
        }

        for (int i = 0; i < moduleSeeds.size(); i++) {
            KnowledgeNode node = createModuleNode(tree.getId(), root.getId(), moduleSeeds.get(i), i + 1, now);
            nodeMapper.insert(node);
            nodes.add(node);
        }

        return toTreeResponse(tree, nodes);
    }

    public KnowledgeTreeDtos.TreeResponse getTree(String treeId, Long userId) {
        KnowledgeTree tree = requireOwnedTree(treeId, userId);
        return toTreeResponse(tree, loadNodes(treeId));
    }

    public KnowledgeTreeDtos.TreeResponse getByPlanInternal(Long planId, Long userId) {
        requireOwnedPlan(planId, userId);
        KnowledgeTree tree = treeMapper.selectOne(new LambdaQueryWrapper<KnowledgeTree>()
                .eq(KnowledgeTree::getPlanId, planId)
                .eq(KnowledgeTree::getUserId, userId));
        if (tree == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        return toTreeResponse(tree, loadNodes(tree.getId()));
    }

    @Transactional
    public KnowledgeTreeDtos.NodeResponse createNodeInternal(KnowledgeTreeDtos.CreateNodeRequest request) {
        KnowledgeNode parent = null;
        if (request.getParentId() != null && !request.getParentId().isBlank()) {
            parent = nodeMapper.selectById(request.getParentId());
            if (parent == null) {
                throw new BusinessException(ErrorCode.NOT_FOUND);
            }
        }

        String treeId = request.getTreeId();
        if (parent != null) {
            if (treeId != null && !treeId.isBlank() && !treeId.equals(parent.getTreeId())) {
                throw new BusinessException(ErrorCode.BAD_REQUEST);
            }
            treeId = parent.getTreeId();
        }
        if (treeId == null || treeId.isBlank() || request.getTitle() == null || request.getTitle().isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        if (treeMapper.selectById(treeId) == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }

        LocalDateTime now = LocalDateTime.now();
        KnowledgeNode node = new KnowledgeNode();
        node.setId(request.getId() != null && !request.getId().isBlank() ? request.getId() : nextId("node"));
        node.setTreeId(treeId);
        node.setParentId(request.getParentId());
        node.setResourceId(request.getResourceId());
        node.setTitle(request.getTitle());
        node.setSummary(request.getSummary());
        node.setContent(request.getContent());
        node.setStatus(defaultString(request.getStatus(), STATUS_PENDING));
        node.setRelevance(defaultInt(request.getRelevance(), 0));
        node.setImportance(defaultInt(request.getImportance(), 2));
        node.setRelevanceScore(defaultInt(request.getRelevanceScore(), 2));
        node.setDifficulty(defaultInt(request.getDifficulty(), 2));
        node.setDepth(defaultInt(request.getDepth(), parent != null ? defaultInt(parent.getDepth(), 0) + 1 : 0));
        node.setSortOrder(defaultInt(request.getSortOrder(), 0));
        node.setPrerequisiteIds(toJson(request.getPrerequisiteIds()));
        node.setIsFundamental(defaultBoolean(request.getIsFundamental(), false));
        node.setFpRelation(defaultString(request.getFpRelation(), ""));
        node.setFpReason(request.getFpReason());
        node.setCollapsed(defaultBoolean(request.getCollapsed(), false));
        node.setCreatedAt(now);
        node.setUpdatedAt(now);
        nodeMapper.insert(node);
        return toNodeResponse(node);
    }

    @Transactional
    public KnowledgeTreeDtos.NodeResponse updateNode(String nodeId, Long userId, KnowledgeTreeDtos.UpdateNodeRequest request) {
        KnowledgeNode node = requireOwnedNode(nodeId, userId);
        return updateNode(node, request);
    }

    @Transactional
    public KnowledgeTreeDtos.NodeResponse updateNodeInternal(String nodeId, KnowledgeTreeDtos.UpdateNodeRequest request) {
        KnowledgeNode node = nodeMapper.selectById(nodeId);
        if (node == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        return updateNode(node, request);
    }

    @Transactional
    public TreeMessage addMessageInternal(String nodeId, String role, String content,
                                          List<Object> nextActions, List<Object> searchSources) {
        String normalizedRole = normalizeMessageRole(role);
        if (content == null || content.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        KnowledgeNode node = nodeMapper.selectById(nodeId);
        if (node == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        TreeMessage message = new TreeMessage();
        message.setTreeId(node.getTreeId());
        message.setNodeId(nodeId);
        message.setRole(normalizedRole);
        message.setContent(content);
        message.setNextActions(toJson(nextActions));
        message.setSearchSources(toJson(searchSources));
        message.setCreatedAt(LocalDateTime.now());
        messageMapper.insert(message);
        return message;
    }

    public List<KnowledgeTreeDtos.MessageResponse> getMessages(String nodeId, Long userId) {
        requireOwnedNode(nodeId, userId);
        return getMessagesInternal(nodeId);
    }

    public List<KnowledgeTreeDtos.MessageResponse> getMessagesInternal(String nodeId) {
        if (nodeMapper.selectById(nodeId) == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        return messageMapper.selectList(new LambdaQueryWrapper<TreeMessage>()
                        .eq(TreeMessage::getNodeId, nodeId)
                        .orderByAsc(TreeMessage::getId))
                .stream()
                .map(this::toMessageResponse)
                .collect(Collectors.toList());
    }

    public KnowledgeTreeDtos.MessageResponse toMessageResponse(TreeMessage message) {
        KnowledgeTreeDtos.MessageResponse response = new KnowledgeTreeDtos.MessageResponse();
        response.setId(message.getId());
        response.setTreeId(message.getTreeId());
        response.setNodeId(message.getNodeId());
        response.setRole(message.getRole());
        response.setContent(message.getContent());
        response.setNextActions(parseObjectList(message.getNextActions()));
        response.setSearchSources(parseObjectList(message.getSearchSources()));
        response.setCreatedAt(message.getCreatedAt());
        return response;
    }

    private KnowledgeTreeDtos.NodeResponse updateNode(KnowledgeNode node, KnowledgeTreeDtos.UpdateNodeRequest request) {
        String requestedCurrentNodeId = request.getCurrentNodeId();
        if (requestedCurrentNodeId != null && !requestedCurrentNodeId.isBlank()) {
            KnowledgeNode currentNode = nodeMapper.selectById(requestedCurrentNodeId);
            if (currentNode == null || !Objects.equals(currentNode.getTreeId(), node.getTreeId())) {
                throw new BusinessException(ErrorCode.BAD_REQUEST);
            }
        }

        if (request.getTitle() != null) node.setTitle(request.getTitle());
        if (request.getSummary() != null) node.setSummary(request.getSummary());
        if (request.getContent() != null) node.setContent(request.getContent());
        if (request.getStatus() != null) node.setStatus(request.getStatus());
        if (request.getRelevance() != null) node.setRelevance(request.getRelevance());
        if (request.getImportance() != null) node.setImportance(request.getImportance());
        if (request.getRelevanceScore() != null) node.setRelevanceScore(request.getRelevanceScore());
        if (request.getDifficulty() != null) node.setDifficulty(request.getDifficulty());
        if (request.getDepth() != null) node.setDepth(request.getDepth());
        if (request.getSortOrder() != null) node.setSortOrder(request.getSortOrder());
        if (request.getPrerequisiteIds() != null) node.setPrerequisiteIds(toJson(request.getPrerequisiteIds()));
        if (request.getIsFundamental() != null) node.setIsFundamental(request.getIsFundamental());
        if (request.getFpRelation() != null) node.setFpRelation(request.getFpRelation());
        if (request.getFpReason() != null) node.setFpReason(request.getFpReason());
        if (request.getCollapsed() != null) node.setCollapsed(request.getCollapsed());
        node.setUpdatedAt(LocalDateTime.now());
        nodeMapper.updateById(node);

        if (requestedCurrentNodeId != null && !requestedCurrentNodeId.isBlank()) {
            KnowledgeTree tree = treeMapper.selectById(node.getTreeId());
            if (tree != null) {
                tree.setCurrentNodeId(requestedCurrentNodeId);
                tree.setUpdatedAt(LocalDateTime.now());
                treeMapper.updateById(tree);
            }
        }
        return toNodeResponse(node);
    }

    private LearningPlan requireOwnedPlan(Long planId, Long userId) {
        LearningPlan plan = planMapper.selectById(planId);
        if (plan == null || !Objects.equals(plan.getUserId(), userId)) {
            throw new BusinessException(ErrorCode.PLAN_NOT_FOUND);
        }
        return plan;
    }

    private KnowledgeTree requireOwnedTree(String treeId, Long userId) {
        KnowledgeTree tree = treeMapper.selectById(treeId);
        if (tree == null || !Objects.equals(tree.getUserId(), userId)) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        return tree;
    }

    private KnowledgeNode requireOwnedNode(String nodeId, Long userId) {
        KnowledgeNode node = nodeMapper.selectById(nodeId);
        if (node == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        requireOwnedTree(node.getTreeId(), userId);
        return node;
    }

    private List<KnowledgeNode> loadNodes(String treeId) {
        List<KnowledgeNode> nodes = nodeMapper.selectList(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getTreeId, treeId)
                .orderByAsc(KnowledgeNode::getDepth)
                .orderByAsc(KnowledgeNode::getSortOrder)
                .orderByAsc(KnowledgeNode::getCreatedAt));
        return nodes != null ? nodes : List.of();
    }

    private KnowledgeNode createModuleNode(String treeId, String rootId, ModuleSeed seed, int sortOrder, LocalDateTime now) {
        KnowledgeNode node = new KnowledgeNode();
        node.setId(nextId("node"));
        node.setTreeId(treeId);
        node.setParentId(rootId);
        node.setResourceId(seed.resourceId());
        node.setTitle(seed.title());
        node.setSummary(seed.summary());
        node.setContent(seed.content());
        node.setStatus(STATUS_PENDING);
        node.setRelevance(0);
        node.setImportance(2);
        node.setRelevanceScore(2);
        node.setDifficulty(2);
        node.setDepth(1);
        node.setSortOrder(sortOrder);
        node.setPrerequisiteIds(null);
        node.setIsFundamental(false);
        node.setFpRelation("");
        node.setCollapsed(false);
        node.setCreatedAt(now);
        node.setUpdatedAt(now);
        return node;
    }

    private List<ModuleSeed> moduleSeedsFromLearningGoal(String learningGoal) {
        JsonNode root = parseJson(learningGoal);
        JsonNode modules = findArrayField(root, "modules", 0);
        if (modules == null || modules.isEmpty()) {
            return List.of();
        }
        List<ModuleSeed> seeds = new ArrayList<>();
        for (JsonNode module : modules) {
            String title = firstText(module, "title", "module_title", "name");
            if (title == null || title.isBlank()) {
                title = module.isTextual() ? module.asText() : "学习模块 " + (seeds.size() + 1);
            }
            String summary = firstText(module, "description", "summary", "content");
            seeds.add(new ModuleSeed(title, summary, module.isObject() ? module.toString() : null, null));
        }
        return seeds;
    }

    private List<ModuleSeed> moduleSeedsFromResources(Long planId) {
        List<LearningResource> resources = resourceMapper.selectList(new LambdaQueryWrapper<LearningResource>()
                .eq(LearningResource::getPlanId, planId)
                .orderByAsc(LearningResource::getModuleOrder)
                .orderByAsc(LearningResource::getId));
        if (resources == null || resources.isEmpty()) {
            return List.of();
        }
        Map<Integer, List<LearningResource>> grouped = resources.stream()
                .sorted(Comparator.comparing((LearningResource r) -> defaultInt(r.getModuleOrder(), 0))
                        .thenComparing(r -> defaultLong(r.getId(), 0L)))
                .collect(Collectors.groupingBy(
                        r -> defaultInt(r.getModuleOrder(), 0),
                        LinkedHashMap::new,
                        Collectors.toList()));

        List<ModuleSeed> seeds = new ArrayList<>();
        int index = 1;
        for (Map.Entry<Integer, List<LearningResource>> entry : grouped.entrySet()) {
            LearningResource first = entry.getValue().get(0);
            JsonNode moduleData = parseJson(first.getModuleData());
            String title = firstText(moduleData, "module_title", "title", "name");
            if (title == null || title.isBlank()) {
                title = "模块 " + index;
            }
            String summary = firstText(moduleData, "description", "summary", "content");
            seeds.add(new ModuleSeed(title, summary, first.getModuleData(), first.getId()));
            index++;
        }
        return seeds;
    }

    private KnowledgeTreeDtos.TreeResponse toTreeResponse(KnowledgeTree tree, List<KnowledgeNode> nodes) {
        KnowledgeTreeDtos.TreeResponse response = new KnowledgeTreeDtos.TreeResponse();
        response.setTree(toTreeDto(tree));
        response.setNodes(nodes.stream().map(this::toNodeResponse).collect(Collectors.toList()));
        return response;
    }

    private KnowledgeTreeDtos.TreeDto toTreeDto(KnowledgeTree tree) {
        KnowledgeTreeDtos.TreeDto dto = new KnowledgeTreeDtos.TreeDto();
        dto.setId(tree.getId());
        dto.setPlanId(tree.getPlanId());
        dto.setUserId(tree.getUserId());
        dto.setTitle(tree.getTitle());
        dto.setField(tree.getField());
        dto.setCurrentProblem(tree.getCurrentProblem());
        dto.setLearningBackground(tree.getLearningBackground());
        dto.setCurrentNodeId(tree.getCurrentNodeId());
        dto.setContextSummary(tree.getContextSummary());
        dto.setCreatedAt(tree.getCreatedAt());
        dto.setUpdatedAt(tree.getUpdatedAt());
        return dto;
    }

    private KnowledgeTreeDtos.NodeResponse toNodeResponse(KnowledgeNode node) {
        KnowledgeTreeDtos.NodeResponse response = new KnowledgeTreeDtos.NodeResponse();
        response.setId(node.getId());
        response.setTreeId(node.getTreeId());
        response.setParentId(node.getParentId());
        response.setResourceId(node.getResourceId());
        response.setTitle(node.getTitle());
        response.setSummary(node.getSummary());
        response.setContent(node.getContent());
        response.setStatus(node.getStatus());
        response.setRelevance(node.getRelevance());
        response.setImportance(node.getImportance());
        response.setRelevanceScore(node.getRelevanceScore());
        response.setDifficulty(node.getDifficulty());
        response.setDepth(node.getDepth());
        response.setSortOrder(node.getSortOrder());
        response.setPrerequisiteIds(parseStringList(node.getPrerequisiteIds()));
        response.setIsFundamental(node.getIsFundamental());
        response.setFpRelation(node.getFpRelation());
        response.setFpReason(node.getFpReason());
        response.setCollapsed(node.getCollapsed());
        response.setCreatedAt(node.getCreatedAt());
        response.setUpdatedAt(node.getUpdatedAt());
        return response;
    }

    private JsonNode parseJson(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            JsonNode node = objectMapper.readTree(value);
            if (node.isTextual()) {
                String text = node.asText();
                if (text != null && (text.trim().startsWith("{") || text.trim().startsWith("["))) {
                    return objectMapper.readTree(text);
                }
            }
            return node;
        } catch (Exception ignored) {
            return null;
        }
    }

    private JsonNode findArrayField(JsonNode node, String fieldName, int depth) {
        if (node == null || depth > 4) {
            return null;
        }
        if (node.isObject()) {
            JsonNode direct = node.get(fieldName);
            if (direct != null && direct.isArray()) {
                return direct;
            }
            for (JsonNode child : node) {
                JsonNode found = findArrayField(child, fieldName, depth + 1);
                if (found != null) {
                    return found;
                }
            }
        }
        if (node.isArray()) {
            return node;
        }
        return null;
    }

    private String firstText(JsonNode node, String... fieldNames) {
        if (node == null || !node.isObject()) {
            return null;
        }
        for (String fieldName : fieldNames) {
            JsonNode value = node.get(fieldName);
            if (value != null && value.isValueNode()) {
                String text = value.asText();
                if (text != null && !text.isBlank()) {
                    return text;
                }
            }
        }
        return null;
    }

    private List<String> parseStringList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            JsonNode node = objectMapper.readTree(json);
            if (!node.isArray()) {
                return List.of();
            }
            List<String> values = new ArrayList<>();
            node.forEach(item -> values.add(item.asText()));
            return values;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Object> parseObjectList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(
                    json,
                    objectMapper.getTypeFactory().constructCollectionType(List.class, Object.class));
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private String toJson(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
    }

    private String normalizeMessageRole(String role) {
        if (role == null || role.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        String normalized = role.trim().toUpperCase();
        if (!MESSAGE_ROLES.contains(normalized)) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        return normalized;
    }

    private String nextId(String prefix) {
        return prefix + "_" + UUID.randomUUID().toString().replace("-", "");
    }

    private String defaultString(String value, String fallback) {
        return value != null ? value : fallback;
    }

    private Integer defaultInt(Integer value, Integer fallback) {
        return value != null ? value : fallback;
    }

    private Boolean defaultBoolean(Boolean value, Boolean fallback) {
        return value != null ? value : fallback;
    }

    private Long defaultLong(Long value, Long fallback) {
        return value != null ? value : fallback;
    }

    private record ModuleSeed(String title, String summary, String content, Long resourceId) {
    }
}
