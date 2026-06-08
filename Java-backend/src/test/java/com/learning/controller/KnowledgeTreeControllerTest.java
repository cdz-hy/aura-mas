package com.learning.controller;

import com.learning.common.Result;
import com.learning.dto.KnowledgeTreeDtos;
import com.learning.entity.TreeMessage;
import com.learning.service.KnowledgeTreeService;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class KnowledgeTreeControllerTest {

    private final KnowledgeTreeService service = mock(KnowledgeTreeService.class);
    private final KnowledgeTreeController controller = new KnowledgeTreeController(service);
    private final Authentication authentication = new UsernamePasswordAuthenticationToken(7L, null);

    @Test
    void publicCreateByPlanUsesAuthenticatedUser() {
        KnowledgeTreeDtos.TreeResponse response = new KnowledgeTreeDtos.TreeResponse();
        KnowledgeTreeDtos.TreeDto tree = new KnowledgeTreeDtos.TreeDto();
        tree.setId("tree_a");
        response.setTree(tree);
        when(service.createOrGetByPlan(12L, 7L)).thenReturn(response);

        Result<KnowledgeTreeDtos.TreeResponse> result = controller.createOrGetByPlan(authentication, 12L);

        assertEquals("tree_a", result.getData().getTree().getId());
        verify(service).createOrGetByPlan(12L, 7L);
    }

    @Test
    void publicUpdateNodeUsesAuthenticatedUser() {
        KnowledgeTreeDtos.NodeResponse node = new KnowledgeTreeDtos.NodeResponse();
        node.setId("node_a");
        KnowledgeTreeDtos.UpdateNodeRequest request = new KnowledgeTreeDtos.UpdateNodeRequest();
        request.setCollapsed(true);
        when(service.updateNode("node_a", 7L, request)).thenReturn(node);

        Result<KnowledgeTreeDtos.NodeResponse> result = controller.updateNode(authentication, "node_a", request);

        assertEquals("node_a", result.getData().getId());
        verify(service).updateNode("node_a", 7L, request);
    }

    @Test
    void internalPlanPostUsesExplicitUserId() {
        KnowledgeTreeDtos.TreeResponse response = new KnowledgeTreeDtos.TreeResponse();
        when(service.createOrGetByPlan(12L, 42L)).thenReturn(response);

        controller.createOrGetByPlanInternal(12L, 42L);

        verify(service).createOrGetByPlan(12L, 42L);
    }

    @Test
    void internalCreateNodeDelegatesPayload() {
        KnowledgeTreeDtos.CreateNodeRequest request = new KnowledgeTreeDtos.CreateNodeRequest();
        request.setTreeId("tree_a");
        request.setTitle("新节点");
        KnowledgeTreeDtos.NodeResponse response = new KnowledgeTreeDtos.NodeResponse();
        when(service.createNodeInternal(request)).thenReturn(response);

        controller.createNodeInternal(request);

        verify(service).createNodeInternal(request);
    }

    @Test
    void internalAddMessageDelegatesPayload() {
        KnowledgeTreeDtos.AddMessageRequest request = new KnowledgeTreeDtos.AddMessageRequest();
        request.setRole("USER");
        request.setContent("解释一下");
        request.setNextActions(List.of());
        request.setSearchSources(List.of());
        TreeMessage message = new TreeMessage();
        message.setId(5L);
        KnowledgeTreeDtos.MessageResponse response = new KnowledgeTreeDtos.MessageResponse();
        response.setId(5L);
        when(service.addMessageInternal("node_a", "USER", "解释一下", List.of(), List.of())).thenReturn(message);
        when(service.toMessageResponse(message)).thenReturn(response);

        Result<KnowledgeTreeDtos.MessageResponse> result = controller.addMessageInternal("node_a", request);

        assertEquals(5L, result.getData().getId());
        verify(service).addMessageInternal("node_a", "USER", "解释一下", List.of(), List.of());
        verify(service).toMessageResponse(message);
    }
}
