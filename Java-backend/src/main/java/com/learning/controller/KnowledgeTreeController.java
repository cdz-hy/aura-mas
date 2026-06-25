package com.learning.controller;

import com.learning.common.Result;
import com.learning.dto.KnowledgeTreeDtos;
import com.learning.entity.TreeMessage;
import com.learning.service.KnowledgeTreeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@Tag(name = "交互式知识树")
@RestController
@RequestMapping("/api/knowledge-tree")
@RequiredArgsConstructor
public class KnowledgeTreeController {

    private final KnowledgeTreeService treeService;

    @Operation(summary = "按学习计划创建或获取知识树")
    @PostMapping("/plan/{planId}")
    public Result<KnowledgeTreeDtos.TreeResponse> createOrGetByPlan(Authentication authentication,
                                                                    @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(treeService.createOrGetByPlan(planId, userId));
    }

    @Operation(summary = "获取知识树详情")
    @GetMapping("/{treeId}")
    public Result<KnowledgeTreeDtos.TreeResponse> getTree(Authentication authentication,
                                                          @PathVariable String treeId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(treeService.getTree(treeId, userId));
    }

    @Operation(summary = "更新知识树节点")
    @PatchMapping("/nodes/{nodeId}")
    public Result<KnowledgeTreeDtos.NodeResponse> updateNode(Authentication authentication,
                                                            @PathVariable String nodeId,
                                                            @RequestBody KnowledgeTreeDtos.UpdateNodeRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(treeService.updateNode(nodeId, userId, request));
    }

    @Operation(summary = "获取节点消息")
    @GetMapping("/nodes/{nodeId}/messages")
    public Result<List<KnowledgeTreeDtos.MessageResponse>> getMessages(Authentication authentication,
                                                                       @PathVariable String nodeId) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(treeService.getMessages(nodeId, userId));
    }

    @Operation(summary = "内部接口：按学习计划获取知识树")
    @GetMapping("/internal/plan/{planId}")
    public Result<KnowledgeTreeDtos.TreeResponse> getByPlanInternal(@PathVariable Long planId,
                                                                    @RequestParam Long userId) {
        return Result.success(treeService.getByPlanInternal(planId, userId));
    }

    @Operation(summary = "内部接口：按学习计划创建或获取知识树")
    @PostMapping("/internal/plan/{planId}")
    public Result<KnowledgeTreeDtos.TreeResponse> createOrGetByPlanInternal(@PathVariable Long planId,
                                                                            @RequestParam Long userId) {
        return Result.success(treeService.createOrGetByPlan(planId, userId));
    }

    @Operation(summary = "内部接口：按树 ID 获取知识树")
    @GetMapping("/internal/trees/{treeId}")
    public Result<KnowledgeTreeDtos.TreeResponse> getTreeInternal(@PathVariable String treeId,
                                                                  @RequestParam Long userId) {
        return Result.success(treeService.getTreeInternal(treeId, userId));
    }

    @Operation(summary = "内部接口：创建知识树节点")
    @PostMapping("/internal/nodes")
    public Result<KnowledgeTreeDtos.NodeResponse> createNodeInternal(
            @RequestBody KnowledgeTreeDtos.CreateNodeRequest request) {
        return Result.success(treeService.createNodeInternal(request));
    }

    @Operation(summary = "内部接口：批量创建知识树节点")
    @PostMapping("/internal/nodes/batch")
    public Result<KnowledgeTreeDtos.BatchCreateNodesResponse> createNodesBatchInternal(
            @RequestBody KnowledgeTreeDtos.BatchCreateNodesRequest request) {
        return Result.success(treeService.createNodesBatchInternal(request));
    }

    @Operation(summary = "内部接口：更新知识树节点")
    @PatchMapping("/internal/nodes/{nodeId}")
    public Result<KnowledgeTreeDtos.NodeResponse> updateNodeInternal(
            @PathVariable String nodeId,
            @RequestBody KnowledgeTreeDtos.UpdateNodeRequest request) {
        return Result.success(treeService.updateNodeInternal(nodeId, request));
    }

    @Operation(summary = "内部接口：校验节点归属")
    @GetMapping("/internal/trees/{treeId}/nodes/{nodeId}/verify")
    public Result<Boolean> verifyNodeInternal(@PathVariable String treeId,
                                              @PathVariable String nodeId,
                                              @RequestParam Long userId) {
        treeService.assertNodeBelongsToUserAndTree(treeId, nodeId, userId);
        return Result.success(true);
    }

    @Operation(summary = "内部接口：添加节点消息")
    @PostMapping("/internal/nodes/{nodeId}/messages")
    public Result<KnowledgeTreeDtos.MessageResponse> addMessageInternal(
            @PathVariable String nodeId,
            @RequestBody KnowledgeTreeDtos.AddMessageRequest request) {
        TreeMessage saved = treeService.addMessageInternal(
                nodeId,
                request.getRole(),
                request.getContent(),
                request.getNextActions(),
                request.getSearchSources()
        );
        return Result.success(treeService.toMessageResponse(saved));
    }

    @Operation(summary = "内部接口：获取节点消息")
    @GetMapping("/internal/nodes/{nodeId}/messages")
    public Result<List<KnowledgeTreeDtos.MessageResponse>> getMessagesInternal(@PathVariable String nodeId) {
        return Result.success(treeService.getMessagesInternal(nodeId));
    }

    @Operation(summary = "内部接口：更新知识树元数据")
    @PatchMapping("/internal/trees/{treeId}")
    public Result<KnowledgeTreeDtos.TreeResponse> updateTreeInternal(
            @PathVariable String treeId,
            @RequestBody KnowledgeTreeDtos.UpdateTreeRequest request) {
        return Result.success(treeService.updateTreeInternal(treeId, request));
    }

    @Operation(summary = "内部接口：同步任务分解到知识树")
    @PostMapping("/internal/plan/{planId}/sync-breakdown")
    public Result<KnowledgeTreeDtos.TreeResponse> syncTaskBreakdownInternal(
            @PathVariable Long planId,
            @RequestBody KnowledgeTreeDtos.SyncTaskBreakdownRequest request) {
        Long userId = request.getUserId();
        if (userId == null) {
            return Result.error("userId required");
        }
        return Result.success(treeService.syncTaskBreakdownInternal(planId, userId, request));
    }
}
