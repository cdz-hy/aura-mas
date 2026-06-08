package com.learning.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.dto.KnowledgeTreeDtos;
import com.learning.entity.KnowledgeNode;
import com.learning.entity.KnowledgeTree;
import com.learning.entity.LearningPlan;
import com.learning.entity.TreeMessage;
import com.learning.exception.BusinessException;
import com.learning.mapper.KnowledgeNodeMapper;
import com.learning.mapper.KnowledgeTreeMapper;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.TreeMessageMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.atLeast;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class KnowledgeTreeServiceTest {

    private KnowledgeTreeMapper treeMapper;
    private KnowledgeNodeMapper nodeMapper;
    private TreeMessageMapper messageMapper;
    private LearningPlanMapper planMapper;
    private LearningResourceMapper resourceMapper;
    private KnowledgeTreeService service;

    @BeforeEach
    void setUp() {
        treeMapper = mock(KnowledgeTreeMapper.class);
        nodeMapper = mock(KnowledgeNodeMapper.class);
        messageMapper = mock(TreeMessageMapper.class);
        planMapper = mock(LearningPlanMapper.class);
        resourceMapper = mock(LearningResourceMapper.class);
        service = new KnowledgeTreeService(
                treeMapper,
                nodeMapper,
                messageMapper,
                planMapper,
                resourceMapper,
                new ObjectMapper()
        );
    }

    @Test
    void createTreeFromPlanCreatesRootAndModuleNodes() {
        LearningPlan plan = new LearningPlan();
        plan.setId(12L);
        plan.setUserId(7L);
        plan.setTitle("机器学习");
        plan.setLearningGoal("{\"modules\":[{\"title\":\"线性回归\",\"description\":\"建模基础\"}]}");
        when(planMapper.selectById(12L)).thenReturn(plan);
        when(resourceMapper.selectList(any())).thenReturn(List.of());

        KnowledgeTreeDtos.TreeResponse response = service.createOrGetByPlan(12L, 7L);

        assertEquals(12L, response.getTree().getPlanId());
        assertEquals("机器学习", response.getTree().getTitle());
        verify(treeMapper).insert(any(KnowledgeTree.class));
        verify(nodeMapper, atLeast(2)).insert(any(KnowledgeNode.class));
    }

    @Test
    void createTreeRejectsWrongOwner() {
        LearningPlan plan = new LearningPlan();
        plan.setId(12L);
        plan.setUserId(99L);
        when(planMapper.selectById(12L)).thenReturn(plan);

        assertThrows(BusinessException.class, () -> service.createOrGetByPlan(12L, 7L));
    }

    @Test
    void addMessagePersistsNodeScopedMessage() {
        KnowledgeNode node = new KnowledgeNode();
        node.setId("node_a");
        node.setTreeId("tree_a");
        when(nodeMapper.selectById("node_a")).thenReturn(node);

        TreeMessage saved = service.addMessageInternal("node_a", "USER", "解释一下", List.of(), List.of());

        assertEquals("node_a", saved.getNodeId());
        assertEquals("USER", saved.getRole());
        verify(messageMapper).insert(any(TreeMessage.class));
    }

    @Test
    void createNodeInternalRejectsParentFromDifferentTree() {
        KnowledgeNode parent = new KnowledgeNode();
        parent.setId("parent_a");
        parent.setTreeId("tree_a");
        when(nodeMapper.selectById("parent_a")).thenReturn(parent);

        KnowledgeTree tree = new KnowledgeTree();
        tree.setId("tree_b");
        when(treeMapper.selectById("tree_b")).thenReturn(tree);

        KnowledgeTreeDtos.CreateNodeRequest request = new KnowledgeTreeDtos.CreateNodeRequest();
        request.setTreeId("tree_b");
        request.setParentId("parent_a");
        request.setTitle("跨树节点");

        assertThrows(BusinessException.class, () -> service.createNodeInternal(request));
        verify(nodeMapper, never()).insert(any(KnowledgeNode.class));
    }

    @Test
    void updateNodeRejectsCurrentNodeFromDifferentTree() {
        KnowledgeNode node = new KnowledgeNode();
        node.setId("node_a");
        node.setTreeId("tree_a");
        when(nodeMapper.selectById("node_a")).thenReturn(node);

        KnowledgeNode candidate = new KnowledgeNode();
        candidate.setId("node_b");
        candidate.setTreeId("tree_b");
        when(nodeMapper.selectById("node_b")).thenReturn(candidate);

        KnowledgeTreeDtos.UpdateNodeRequest request = new KnowledgeTreeDtos.UpdateNodeRequest();
        request.setCurrentNodeId("node_b");

        assertThrows(BusinessException.class, () -> service.updateNodeInternal("node_a", request));
        verify(nodeMapper, never()).updateById(any(KnowledgeNode.class));
        verify(treeMapper, never()).updateById(any(KnowledgeTree.class));
    }

    @Test
    void addMessageInternalRejectsInvalidPayload() {
        KnowledgeNode node = new KnowledgeNode();
        node.setId("node_a");
        node.setTreeId("tree_a");
        when(nodeMapper.selectById("node_a")).thenReturn(node);

        assertThrows(BusinessException.class,
                () -> service.addMessageInternal("node_a", "", "解释一下", List.of(), List.of()));
        assertThrows(BusinessException.class,
                () -> service.addMessageInternal("node_a", "USER", " ", List.of(), List.of()));
        assertThrows(BusinessException.class,
                () -> service.addMessageInternal("node_a", "MODERATOR", "解释一下", List.of(), List.of()));

        TreeMessage saved = service.addMessageInternal("node_a", "assistant", "解释一下", List.of(), List.of());

        assertEquals("ASSISTANT", saved.getRole());
        verify(messageMapper).insert(any(TreeMessage.class));
    }
}
