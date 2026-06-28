package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
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
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class KnowledgeTreeService {

    private static final String STATUS_PENDING = "pending";
    private static final int MAX_TREE_DEPTH = 3;
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
            List<KnowledgeNode> nodes = loadNodes(existing.getId());
            // 自愈：树只有根节点但 DB 已有资源时，自动补建 L1 模块
            if (needsL1SelfHeal(nodes)) {
                List<ModuleSeed> seeds = moduleSeedsFromResources(planId);
                if (!seeds.isEmpty()) {
                    nodes = reconcilePrimaryModules(existing, nodes, seeds);
                }
            }
            return toTreeResponse(existing, nodes);
        }

        LocalDateTime now = LocalDateTime.now();
        KnowledgeTree tree = new KnowledgeTree();
        tree.setId(nextId("tree"));
        tree.setPlanId(planId);
        tree.setUserId(userId);
        tree.setTitle(plan.getTitle());
        tree.setField(extractField(plan.getLearningGoal()));
        tree.setCurrentProblem(plan.getTitle());
        tree.setLearningBackground(extractLearningBackground(plan.getLearningGoal(), plan.getTitle()));
        tree.setContextSummary(extractContextSummary(plan.getLearningGoal(), plan.getTitle()));
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
        List<ModuleSeed> moduleSeeds = moduleSeedsFromResources(planId);
        if (moduleSeeds.isEmpty()) {
            moduleSeeds = moduleSeedsFromLearningGoal(plan.getLearningGoal());
        }
        if (!moduleSeeds.isEmpty()) {
            insertModuleNodesBatch(tree.getId(), root.getId(), moduleSeeds, now, nodes);
        }
        for (KnowledgeNode node : nodes) {
            if (node.getResourceId() != null && !Objects.equals(node.getId(), root.getId())) {
                linkResourceToNode(node.getResourceId(), node.getId(), node.getTitle());
            }
        }

        return toTreeResponse(tree, nodes);
    }

    /** 判断树是否需要自愈 L1 节点：有根节点但没有任何 L1 子节点。 */
    private boolean needsL1SelfHeal(List<KnowledgeNode> nodes) {
        KnowledgeNode root = nodes.stream()
                .filter(n -> n.getParentId() == null || n.getParentId().isBlank())
                .findFirst()
                .orElse(null);
        if (root == null) {
            return false;
        }
        boolean hasL1Children = nodes.stream()
                .anyMatch(n -> Objects.equals(root.getId(), n.getParentId()));
        return !hasL1Children;
    }

    /** 批量创建一级模块节点，减少 DB 往返。 */
    private void insertModuleNodesBatch(String treeId, String rootId, List<ModuleSeed> moduleSeeds, LocalDateTime now, List<KnowledgeNode> nodes) {
        if (moduleSeeds.isEmpty()) {
            return;
        }
        KnowledgeTreeDtos.BatchCreateNodesRequest batch = new KnowledgeTreeDtos.BatchCreateNodesRequest();
        List<KnowledgeTreeDtos.CreateNodeRequest> requests = new ArrayList<>();
        for (int i = 0; i < moduleSeeds.size(); i++) {
            ModuleSeed seed = moduleSeeds.get(i);
            KnowledgeTreeDtos.CreateNodeRequest req = new KnowledgeTreeDtos.CreateNodeRequest();
            req.setTreeId(treeId);
            req.setParentId(rootId);
            req.setResourceId(seed.resourceId());
            req.setTitle(seed.title());
            req.setSummary(seed.summary());
            req.setContent(seed.content());
            req.setStatus(STATUS_PENDING);
            req.setRelevance(0);
            req.setImportance(2);
            req.setRelevanceScore(2);
            req.setDifficulty(2);
            req.setDepth(1);
            req.setSortOrder(i + 1);
            req.setCollapsed(false);
            requests.add(req);
        }
        batch.setNodes(requests);
        List<KnowledgeNode> created = createNodesBatchInternal(batch).getNodes().stream()
                .map(this::toEntity)
                .collect(Collectors.toList());
        nodes.addAll(created);
    }

    private KnowledgeNode toEntity(KnowledgeTreeDtos.NodeResponse response) {
        KnowledgeNode node = new KnowledgeNode();
        node.setId(response.getId());
        node.setTreeId(response.getTreeId());
        node.setParentId(response.getParentId());
        node.setResourceId(response.getResourceId());
        node.setTitle(response.getTitle());
        node.setSummary(response.getSummary());
        node.setContent(response.getContent());
        node.setStatus(response.getStatus());
        node.setRelevance(response.getRelevance());
        node.setImportance(response.getImportance());
        node.setRelevanceScore(response.getRelevanceScore());
        node.setDifficulty(response.getDifficulty());
        node.setDepth(response.getDepth());
        node.setSortOrder(response.getSortOrder());
        node.setPrerequisiteIds(toJson(response.getPrerequisiteIds()));
        node.setIsFundamental(response.getIsFundamental());
        node.setFpRelation(response.getFpRelation());
        node.setFpReason(response.getFpReason());
        node.setCollapsed(response.getCollapsed());
        node.setCreatedAt(response.getCreatedAt());
        node.setUpdatedAt(response.getUpdatedAt());
        return node;
    }

    /** 将计划资源与知识树一级模块对齐：每个 moduleOrder 对应一个主节点，并双向绑定 resourceId/nodeId。 */
    private List<KnowledgeNode> syncResourceNodes(KnowledgeTree tree, List<KnowledgeNode> nodes) {
        List<ModuleSeed> seeds = moduleSeedsFromResources(tree.getPlanId());
        if (seeds.isEmpty()) {
            return nodes;
        }
        return reconcilePrimaryModules(tree, nodes, seeds);
    }

    private List<KnowledgeNode> reconcilePrimaryModules(KnowledgeTree tree, List<KnowledgeNode> nodes, List<ModuleSeed> seeds) {
        KnowledgeNode root = nodes.stream()
                .filter(node -> node.getParentId() == null || node.getParentId().isBlank())
                .findFirst()
                .orElseGet(() -> nodes.stream()
                        .filter(node -> defaultInt(node.getDepth(), 0) == 0)
                        .findFirst()
                        .orElse(null));
        if (root == null || seeds.isEmpty()) {
            return nodes;
        }

        List<KnowledgeNode> synced = new ArrayList<>(nodes);
        List<KnowledgeNode> l1Modules = synced.stream()
                .filter(node -> Objects.equals(root.getId(), node.getParentId()))
                .sorted(Comparator.comparing(node -> defaultInt(node.getSortOrder(), 0)))
                .collect(Collectors.toList());

        boolean changed = false;
        LocalDateTime now = LocalDateTime.now();
        int nextSortOrder = l1Modules.stream()
                .map(KnowledgeNode::getSortOrder)
                .filter(Objects::nonNull)
                .max(Integer::compareTo)
                .orElse(0) + 1;

        for (int index = 0; index < seeds.size(); index++) {
            ModuleSeed seed = seeds.get(index);
            KnowledgeNode target;
            if (index < l1Modules.size()) {
                target = l1Modules.get(index);
                if (shouldReplaceTitle(target.getTitle(), seed.title())) {
                    target.setTitle(seed.title());
                    if (seed.summary() != null && !seed.summary().isBlank()) {
                        target.setSummary(seed.summary());
                    }
                    target.setUpdatedAt(now);
                    nodeMapper.updateById(target);
                    changed = true;
                }
            } else {
                target = createModuleNode(tree.getId(), root.getId(), seed, nextSortOrder++, now);
                nodeMapper.insert(target);
                synced.add(target);
                l1Modules.add(target);
                changed = true;
            }

            if (seed.resourceId() != null && !Objects.equals(target.getResourceId(), seed.resourceId())) {
                target.setResourceId(seed.resourceId());
                target.setUpdatedAt(now);
                nodeMapper.updateById(target);
                changed = true;
            }
            if (seed.resourceId() != null) {
                changed |= linkResourceToNode(seed.resourceId(), target.getId(), seed.title());
            }
        }

        // 删除多余的占位一级节点（如单独的「学习模块 1」）
        for (int index = seeds.size(); index < l1Modules.size(); index++) {
            KnowledgeNode orphan = l1Modules.get(index);
            if (!isGenericModuleTitle(orphan.getTitle())) {
                continue;
            }
            if (hasChildNodes(synced, orphan.getId())) {
                continue;
            }
            nodeMapper.deleteById(orphan.getId());
            synced.removeIf(node -> Objects.equals(node.getId(), orphan.getId()));
            changed = true;
        }

        if (changed) {
            tree.setUpdatedAt(now);
            treeMapper.updateById(tree);
        }
        return synced;
    }

    private boolean hasChildNodes(List<KnowledgeNode> nodes, String parentId) {
        return nodes.stream().anyMatch(node -> Objects.equals(parentId, node.getParentId()));
    }

    private boolean shouldReplaceTitle(String currentTitle, String nextTitle) {
        if (nextTitle == null || nextTitle.isBlank()) {
            return false;
        }
        if (currentTitle == null || currentTitle.isBlank()) {
            return true;
        }
        if (isGenericModuleTitle(currentTitle) && !isGenericModuleTitle(nextTitle)) {
            return true;
        }
        return isGenericModuleTitle(currentTitle)
                && !normalizeTitle(currentTitle).equals(normalizeTitle(nextTitle));
    }

    private boolean isGenericModuleTitle(String title) {
        if (title == null || title.isBlank()) {
            return true;
        }
        String normalized = title.trim();
        return normalized.matches("^(学习模块|模块|Module)\\s*\\d+$");
    }

    private boolean linkResourceToNode(Long resourceId, String nodeId, String title) {
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource == null) {
            return false;
        }
        JsonNode data = parseJson(resource.getModuleData());
        ObjectNode moduleData = data != null && data.isObject()
                ? ((ObjectNode) data).deepCopy()
                : objectMapper.createObjectNode();
        boolean changed = false;
        if (!nodeId.equals(moduleData.path("nodeId").asText(null))) {
            moduleData.put("nodeId", nodeId);
            changed = true;
        }
        if (title != null && !title.isBlank()) {
            String moduleTitle = moduleData.path("module_title").asText("");
            if (moduleTitle.isBlank() || isGenericModuleTitle(moduleTitle)) {
                moduleData.put("module_title", title);
                changed = true;
            }
            if (moduleData.path("title").asText("").isBlank()) {
                moduleData.put("title", title);
                changed = true;
            }
        }
        if (!changed) {
            return false;
        }
        try {
            resource.setModuleData(objectMapper.writeValueAsString(moduleData));
        } catch (Exception e) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        resourceMapper.updateById(resource);
        return true;
    }

    @Transactional
    public KnowledgeTreeDtos.TreeResponse getTree(String treeId, Long userId) {
        KnowledgeTree tree = requireOwnedTree(treeId, userId);
        List<KnowledgeNode> nodes = loadNodes(treeId);
        return toTreeResponse(tree, nodes);
    }

    @Transactional
    public KnowledgeTreeDtos.TreeResponse getByPlanInternal(Long planId, Long userId) {
        requireOwnedPlan(planId, userId);
        KnowledgeTree tree = treeMapper.selectOne(new LambdaQueryWrapper<KnowledgeTree>()
                .eq(KnowledgeTree::getPlanId, planId)
                .eq(KnowledgeTree::getUserId, userId));
        if (tree == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        List<KnowledgeNode> nodes = loadNodes(tree.getId());
        return toTreeResponse(tree, nodes);
    }

    public KnowledgeTreeDtos.TreeResponse getTreeInternal(String treeId, Long userId) {
        return getTree(treeId, userId);
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
        node.setDepth(resolveNodeDepth(parent, request.getDepth()));
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
    public KnowledgeTreeDtos.BatchCreateNodesResponse createNodesBatchInternal(
            KnowledgeTreeDtos.BatchCreateNodesRequest request) {
        List<KnowledgeNode> created = new ArrayList<>();
        for (KnowledgeTreeDtos.CreateNodeRequest nodeRequest : request.getNodes()) {
            KnowledgeNode parent = null;
            if (nodeRequest.getParentId() != null && !nodeRequest.getParentId().isBlank()) {
                parent = nodeMapper.selectById(nodeRequest.getParentId());
                if (parent == null) {
                    // 批量创建中父节点可能在同批次中刚创建，从 created 列表查找
                    parent = created.stream()
                            .filter(n -> n.getId().equals(nodeRequest.getParentId()))
                            .findFirst()
                            .orElse(null);
                }
            }

            String treeId = nodeRequest.getTreeId();
            if (parent != null) {
                if (treeId != null && !treeId.isBlank() && !treeId.equals(parent.getTreeId())) {
                    throw new BusinessException(ErrorCode.BAD_REQUEST);
                }
                treeId = parent.getTreeId();
            }
            if (treeId == null || treeId.isBlank() || nodeRequest.getTitle() == null || nodeRequest.getTitle().isBlank()) {
                throw new BusinessException(ErrorCode.BAD_REQUEST);
            }

            LocalDateTime now = LocalDateTime.now();
            KnowledgeNode node = new KnowledgeNode();
            node.setId(nodeRequest.getId() != null && !nodeRequest.getId().isBlank() ? nodeRequest.getId() : nextId("node"));
            node.setTreeId(treeId);
            node.setParentId(nodeRequest.getParentId());
            node.setResourceId(nodeRequest.getResourceId());
            node.setTitle(nodeRequest.getTitle());
            node.setSummary(nodeRequest.getSummary());
            node.setContent(nodeRequest.getContent());
            node.setStatus(defaultString(nodeRequest.getStatus(), STATUS_PENDING));
            node.setRelevance(defaultInt(nodeRequest.getRelevance(), 0));
            node.setImportance(defaultInt(nodeRequest.getImportance(), 2));
            node.setRelevanceScore(defaultInt(nodeRequest.getRelevanceScore(), 2));
            node.setDifficulty(defaultInt(nodeRequest.getDifficulty(), 2));
            node.setDepth(resolveNodeDepth(parent, nodeRequest.getDepth()));
            node.setSortOrder(defaultInt(nodeRequest.getSortOrder(), 0));
            node.setPrerequisiteIds(toJson(nodeRequest.getPrerequisiteIds()));
            node.setIsFundamental(defaultBoolean(nodeRequest.getIsFundamental(), false));
            node.setFpRelation(defaultString(nodeRequest.getFpRelation(), ""));
            node.setFpReason(nodeRequest.getFpReason());
            node.setCollapsed(defaultBoolean(nodeRequest.getCollapsed(), false));
            node.setCreatedAt(now);
            node.setUpdatedAt(now);
            nodeMapper.insert(node);
            created.add(node);
        }

        KnowledgeTreeDtos.BatchCreateNodesResponse response = new KnowledgeTreeDtos.BatchCreateNodesResponse();
        response.setNodes(created.stream().map(this::toNodeResponse).collect(Collectors.toList()));
        return response;
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

    public void assertNodeBelongsToUserAndTree(String treeId, String nodeId, Long userId) {
        KnowledgeNode node = requireOwnedNode(nodeId, userId);
        if (!Objects.equals(node.getTreeId(), treeId)) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
    }

    /**
     * 删除指定节点及其所有后代（硬删除）。
     * 级联删除 tree_message，解除 learning_resource 关联，重置 tree.currentNodeId。
     * 根节点（parentId == null）不可删除。
     */
    @Transactional
    public List<String> deleteNode(String nodeId, Long userId) {
        KnowledgeNode node = requireOwnedNode(nodeId, userId);

        // 禁止删除根节点
        if (node.getParentId() == null || node.getParentId().isBlank()) {
            throw new BusinessException(400, "不能删除根节点");
        }

        String treeId = node.getTreeId();
        List<KnowledgeNode> allNodes = loadNodes(treeId);

        // 递归收集要删除的节点 ID（本节点 + 所有后代）
        Set<String> idsToDelete = new HashSet<>();
        collectDescendantIds(allNodes, nodeId, idsToDelete);
        idsToDelete.add(nodeId);

        // 1. 删除关联的 tree_message
        messageMapper.delete(new LambdaQueryWrapper<TreeMessage>()
                .in(TreeMessage::getNodeId, idsToDelete));

        // 2. 解除 learning_resource 与这些节点的关联
        for (KnowledgeNode n : allNodes) {
            if (idsToDelete.contains(n.getId()) && n.getResourceId() != null) {
                clearResourceNodeLink(n.getResourceId(), n.getId());
            }
        }

        // 3. 删除节点
        nodeMapper.deleteBatchIds(new ArrayList<>(idsToDelete));

        // 4. 如果 tree.currentNodeId 指向被删节点，重置
        KnowledgeTree tree = treeMapper.selectById(treeId);
        if (tree != null && tree.getCurrentNodeId() != null && idsToDelete.contains(tree.getCurrentNodeId())) {
            tree.setCurrentNodeId(node.getParentId());
            tree.setUpdatedAt(LocalDateTime.now());
            treeMapper.updateById(tree);
        }

        return new ArrayList<>(idsToDelete);
    }

    private void collectDescendantIds(List<KnowledgeNode> allNodes, String parentId, Set<String> accumulator) {
        for (KnowledgeNode n : allNodes) {
            if (Objects.equals(parentId, n.getParentId())) {
                accumulator.add(n.getId());
                collectDescendantIds(allNodes, n.getId(), accumulator);
            }
        }
    }

    /** 清除 learning_resource.moduleData 中指向已删节点的 nodeId 引用 */
    private void clearResourceNodeLink(Long resourceId, String nodeId) {
        LearningResource resource = resourceMapper.selectById(resourceId);
        if (resource == null || resource.getModuleData() == null) return;
        try {
            JsonNode data = parseJson(resource.getModuleData());
            if (data != null && data.isObject()) {
                ObjectNode obj = (ObjectNode) data;
                boolean changed = false;
                if (nodeId.equals(textOrNull(obj.get("nodeId")))) {
                    obj.remove("nodeId");
                    changed = true;
                }
                if (nodeId.equals(textOrNull(obj.get("node_id")))) {
                    obj.remove("node_id");
                    changed = true;
                }
                if (changed) {
                    resource.setModuleData(obj.toString());
                    resourceMapper.updateById(resource);
                }
            }
        } catch (Exception ignored) {
            // moduleData 解析失败时跳过
        }
    }

    private String textOrNull(JsonNode node) {
        return node != null && node.isTextual() ? node.asText() : null;
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

        if (request.getParentId() != null) {
            applyReparent(node, request.getParentId(), request.getSortOrder());
        }

        if (request.getTitle() != null) node.setTitle(request.getTitle());
        if (request.getSummary() != null) node.setSummary(request.getSummary());
        if (request.getContent() != null) node.setContent(request.getContent());
        if (request.getStatus() != null) node.setStatus(request.getStatus());
        if (request.getRelevance() != null) node.setRelevance(request.getRelevance());
        if (request.getImportance() != null) node.setImportance(request.getImportance());
        if (request.getRelevanceScore() != null) node.setRelevanceScore(request.getRelevanceScore());
        if (request.getDifficulty() != null) node.setDifficulty(request.getDifficulty());
        if (request.getDepth() != null && request.getParentId() == null) {
            assertDepthWithinLimit(request.getDepth());
            node.setDepth(request.getDepth());
        }
        if (request.getSortOrder() != null) node.setSortOrder(request.getSortOrder());
        if (request.getPrerequisiteIds() != null) node.setPrerequisiteIds(toJson(request.getPrerequisiteIds()));
        if (request.getIsFundamental() != null) node.setIsFundamental(request.getIsFundamental());
        if (request.getFpRelation() != null) node.setFpRelation(request.getFpRelation());
        if (request.getFpReason() != null) node.setFpReason(request.getFpReason());
        if (request.getCollapsed() != null) node.setCollapsed(request.getCollapsed());
        node.setUpdatedAt(LocalDateTime.now());
        nodeMapper.updateById(node);

        if (request.getParentId() != null) {
            recalcDepthForSubtree(node.getId(), defaultInt(node.getDepth(), 0));
        }

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

    /** 校验并应用新的父节点（不写库，由 updateNode 统一持久化）。 */
    private void applyReparent(KnowledgeNode node, String newParentId, Integer requestedSortOrder) {
        if (newParentId.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        if (Objects.equals(node.getId(), newParentId)) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        KnowledgeNode newParent = nodeMapper.selectById(newParentId);
        if (newParent == null || !Objects.equals(newParent.getTreeId(), node.getTreeId())) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
        if (isDescendantOf(node.getTreeId(), newParentId, node.getId())) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }

        node.setParentId(newParentId);
        int parentDepth = defaultInt(newParent.getDepth(), 0);
        int nextDepth = parentDepth + 1;
        assertSubtreeWithinDepthLimit(node.getId(), nextDepth);
        node.setDepth(nextDepth);
        if (requestedSortOrder != null) {
            node.setSortOrder(requestedSortOrder);
        } else {
            node.setSortOrder(nextSortOrderUnderParent(loadNodes(node.getTreeId()), newParentId));
        }
    }

    /** 判断 candidate 是否为 ancestor 的子孙节点。 */
    private boolean isDescendantOf(String treeId, String candidateId, String ancestorId) {
        String cursor = candidateId;
        Set<String> seen = new HashSet<>();
        while (cursor != null && !cursor.isBlank()) {
            if (Objects.equals(cursor, ancestorId)) {
                return true;
            }
            if (!seen.add(cursor)) {
                break;
            }
            KnowledgeNode current = nodeMapper.selectById(cursor);
            if (current == null || !Objects.equals(current.getTreeId(), treeId)) {
                break;
            }
            cursor = current.getParentId();
        }
        return false;
    }

    private void recalcDepthForSubtree(String parentId, int parentDepth) {
        List<KnowledgeNode> children = nodeMapper.selectList(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getParentId, parentId));
        if (children == null || children.isEmpty()) {
            return;
        }
        for (KnowledgeNode child : children) {
            int depth = parentDepth + 1;
            assertDepthWithinLimit(depth);
            child.setDepth(depth);
            child.setUpdatedAt(LocalDateTime.now());
            nodeMapper.updateById(child);
            recalcDepthForSubtree(child.getId(), depth);
        }
    }

    private int resolveNodeDepth(KnowledgeNode parent, Integer requestedDepth) {
        int depth = parent != null
                ? defaultInt(parent.getDepth(), 0) + 1
                : defaultInt(requestedDepth, 0);
        assertDepthWithinLimit(depth);
        return depth;
    }

    private void assertDepthWithinLimit(int depth) {
        if (depth < 0 || depth > MAX_TREE_DEPTH) {
            throw new BusinessException(ErrorCode.BAD_REQUEST);
        }
    }

    private void assertSubtreeWithinDepthLimit(String nodeId, int nextDepth) {
        assertDepthWithinLimit(nextDepth);
        int subtreeHeight = subtreeHeight(nodeId);
        assertDepthWithinLimit(nextDepth + subtreeHeight);
    }

    private int subtreeHeight(String nodeId) {
        List<KnowledgeNode> children = nodeMapper.selectList(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getParentId, nodeId));
        if (children == null || children.isEmpty()) {
            return 0;
        }
        int maxChildHeight = 0;
        for (KnowledgeNode child : children) {
            maxChildHeight = Math.max(maxChildHeight, subtreeHeight(child.getId()));
        }
        return maxChildHeight + 1;
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

    private int nextSortOrderUnderParent(List<KnowledgeNode> nodes, String parentId) {
        return nodes.stream()
                .filter(node -> Objects.equals(parentId, node.getParentId()))
                .map(KnowledgeNode::getSortOrder)
                .filter(Objects::nonNull)
                .max(Integer::compareTo)
                .orElse(0) + 1;
    }

    @Transactional
    public KnowledgeTreeDtos.TreeResponse updateTreeInternal(String treeId, KnowledgeTreeDtos.UpdateTreeRequest request) {
        KnowledgeTree tree = treeMapper.selectById(treeId);
        if (tree == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        if (request.getTitle() != null) tree.setTitle(request.getTitle());
        if (request.getField() != null) tree.setField(request.getField());
        if (request.getCurrentProblem() != null) tree.setCurrentProblem(request.getCurrentProblem());
        if (request.getLearningBackground() != null) tree.setLearningBackground(request.getLearningBackground());
        if (request.getContextSummary() != null) tree.setContextSummary(request.getContextSummary());
        tree.setUpdatedAt(LocalDateTime.now());
        treeMapper.updateById(tree);
        return toTreeResponse(tree, loadNodes(treeId));
    }

    @Transactional
    public KnowledgeTreeDtos.TreeResponse syncTaskBreakdownInternal(Long planId, Long userId,
                                                                      KnowledgeTreeDtos.SyncTaskBreakdownRequest request) {
        KnowledgeTreeDtos.TreeResponse treeResponse = createOrGetByPlan(planId, userId);
        KnowledgeTree tree = treeMapper.selectById(treeResponse.getTree().getId());
        if (tree == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        if (request.getTitle() != null && !request.getTitle().isBlank()) {
            tree.setTitle(request.getTitle());
        }
        if (request.getDescription() != null && !request.getDescription().isBlank()) {
            tree.setContextSummary(request.getDescription());
        }
        if (request.getLearningBackground() != null && !request.getLearningBackground().isBlank()) {
            tree.setLearningBackground(request.getLearningBackground());
        }
        tree.setUpdatedAt(LocalDateTime.now());
        treeMapper.updateById(tree);

        List<KnowledgeNode> nodes = loadNodes(tree.getId());
        KnowledgeNode root = nodes.stream()
                .filter(node -> node.getParentId() == null || node.getParentId().isBlank())
                .findFirst()
                .orElse(null);
        if (root == null || request.getModules() == null || request.getModules().isEmpty()) {
            return toTreeResponse(tree, nodes);
        }

        List<ModuleSeed> breakdownSeeds = new ArrayList<>();
        for (Object rawModule : request.getModules()) {
            JsonNode module = rawModule instanceof JsonNode
                    ? (JsonNode) rawModule
                    : objectMapper.valueToTree(rawModule);
            String title = firstText(module, "title", "module_title", "name");
            if (title == null || title.isBlank()) {
                if (module.isTextual()) {
                    title = module.asText();
                } else {
                    title = "学习模块 " + (breakdownSeeds.size() + 1);
                }
            }
            String summary = firstText(module, "description", "summary", "content");
            breakdownSeeds.add(new ModuleSeed(title, summary, module.isObject() ? module.toString() : null, null));
        }

        List<ModuleSeed> resourceSeeds = moduleSeedsFromResources(planId);
        List<ModuleSeed> seeds = !resourceSeeds.isEmpty() ? resourceSeeds : breakdownSeeds;
        List<KnowledgeNode> synced = reconcilePrimaryModules(tree, nodes, seeds);
        tree.setUpdatedAt(LocalDateTime.now());
        treeMapper.updateById(tree);
        return toTreeResponse(tree, synced);
    }

    private String extractField(String learningGoal) {
        JsonNode root = parseJson(learningGoal);
        return firstText(root, "field", "domain", "subject");
    }

    private String extractContextSummary(String learningGoal, String fallback) {
        JsonNode root = parseJson(learningGoal);
        String summary = firstText(root, "description", "summary", "goal", "learning_goal");
        if (summary != null && !summary.isBlank()) {
            return summary;
        }
        return fallback != null ? fallback : "";
    }

    private String extractLearningBackground(String learningGoal, String fallback) {
        JsonNode root = parseJson(learningGoal);
        String background = firstText(root, "background", "learning_background", "user_background");
        if (background != null && !background.isBlank()) {
            return background;
        }
        return fallback != null ? fallback : "";
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
                if (module.isTextual()) {
                    title = module.asText();
                } else {
                    title = "学习模块 " + (seeds.size() + 1);
                }
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
            if (isGenericModuleTitle(title) && entry.getValue().size() == 1) {
                LearningResource only = entry.getValue().get(0);
                JsonNode onlyData = parseJson(only.getModuleData());
                String better = firstText(onlyData, "module_title", "title", "name");
                if (better != null && !better.isBlank() && !isGenericModuleTitle(better)) {
                    title = better;
                }
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

    /** 标题归一化，用于去重比对 */
    private String normalizeTitle(String value) {
        if (value == null) {
            return "";
        }
        return value.replaceAll("\\s+", "").trim().toLowerCase();
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
