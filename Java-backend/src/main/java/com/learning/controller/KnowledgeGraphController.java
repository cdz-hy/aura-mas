package com.learning.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.Result;
import com.learning.dto.KnowledgeGraphNodePatchReq;
import com.learning.dto.KnowledgeGraphUpdateReq;
import com.learning.entity.UserKnowledgeDomain;
import com.learning.service.UserKnowledgeDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/knowledge-graph")
public class KnowledgeGraphController {

    @Autowired
    private UserKnowledgeDomainService domainService;

    @Autowired
    private ObjectMapper objectMapper;

    /**
     * 获取用户所有的领域列表及图谱概览
     */
    @GetMapping("/user/{userId}")
    public Result<List<UserKnowledgeDomain>> getUserDomains(@PathVariable Long userId) {
        LambdaQueryWrapper<UserKnowledgeDomain> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserKnowledgeDomain::getUserId, userId);
        List<UserKnowledgeDomain> list = domainService.list(wrapper);
        return Result.success(list);
    }

    /**
     * 获取某个具体领域的完整 JSON 图谱
     */
    @GetMapping("/domain/{domainId}")
    public Result<UserKnowledgeDomain> getDomainGraph(@PathVariable Long domainId) {
        UserKnowledgeDomain domain = domainService.getById(domainId);
        if (domain == null) {
            return Result.error("领域不存在");
        }
        return Result.success(domain);
    }

    /**
     * 新建领域图谱初始化数据
     */
    @OperationLog(type = OperationType.KG_CREATE_DOMAIN, module = "KG",
            desc = "'创建知识域: ' + #domainReq.getDomainName()",
            resourceId = "#result?.data?.id?.toString()")
    @PostMapping("/domain")
    public Result<UserKnowledgeDomain> createDomain(@RequestBody UserKnowledgeDomain domainReq) {
        if (domainReq.getUserId() == null || domainReq.getDomainName() == null) {
            return Result.error("userId 和 domainName 不能为空");
        }
        domainService.save(domainReq);
        return Result.success(domainReq);
    }

    /**
     * 保存/更新指定的领域图谱
     */
    @OperationLog(type = OperationType.KG_UPDATE_DOMAIN, module = "KG",
            desc = "'更新知识域ID: ' + #domainId",
            resourceId = "#domainId?.toString()")
    @PutMapping("/domain/{domainId}")
    public Result<Boolean> updateDomainGraph(@PathVariable Long domainId, @RequestBody KnowledgeGraphUpdateReq req) {
        UserKnowledgeDomain domain = domainService.getById(domainId);
        if (domain == null) {
            return Result.error("领域不存在");
        }
        if (req.getDomainName() != null) {
            domain.setDomainName(req.getDomainName());
        }
        if (req.getGraphData() != null) {
            domain.setGraphData(req.getGraphData());
        }
        domain.setUpdatedAt(java.time.LocalDateTime.now());
        boolean success = domainService.updateById(domain);
        return success ? Result.success(true) : Result.error("更新失败");
    }

    /**
     * 供前端单独更新某个节点的属性
     */
    @OperationLog(type = OperationType.KG_PATCH_NODE, module = "KG",
            desc = "'修改知识节点: domain=' + #domainId + ' node=' + #nodeId",
            resourceId = "#domainId?.toString()")
    @PatchMapping("/domain/{domainId}/node/{nodeId}")
    public Result<Boolean> patchNode(@PathVariable Long domainId, @PathVariable String nodeId, @RequestBody KnowledgeGraphNodePatchReq req) {
        UserKnowledgeDomain domain = domainService.getById(domainId);
        if (domain == null) {
            return Result.error("领域不存在");
        }

        Object graphData = domain.getGraphData();
        if (graphData == null) {
            return Result.error("图谱数据为空");
        }

        try {
            // 将 graphData 转换为 Map 结构操作
            Map<String, Object> graphMap = objectMapper.convertValue(graphData, new TypeReference<Map<String, Object>>() {});
            List<Map<String, Object>> nodes = (List<Map<String, Object>>) graphMap.get("nodes");

            if (nodes != null) {
                boolean found = false;
                for (Map<String, Object> node : nodes) {
                    if (nodeId.equals(node.get("id"))) {
                        if (req.getMasteryLevel() != null) {
                            node.put("mastery_level", req.getMasteryLevel());
                        }
                        if (req.getImportance() != null) {
                            node.put("importance", req.getImportance());
                        }
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    return Result.error("未找到对应节点: " + nodeId);
                }

                // 写回更新后的数据
                domain.setGraphData(graphMap);
                domain.setUpdatedAt(java.time.LocalDateTime.now());
                boolean success = domainService.updateById(domain);
                return success ? Result.success(true) : Result.error("节点更新失败");
            }
        } catch (Exception e) {
            return Result.error("更新节点发生异常: " + e.getMessage());
        }

        return Result.error("图谱中无 nodes 节点");
    }
    /**
     * 删除整个领域知识图谱
     */
    @OperationLog(type = OperationType.KG_DELETE_DOMAIN, module = "KG",
            desc = "'删除知识域ID: ' + #domainId",
            resourceId = "#domainId?.toString()")
    @DeleteMapping("/domain/{domainId}")
    public Result<Boolean> deleteDomain(@PathVariable Long domainId) {
        boolean success = domainService.removeById(domainId);
        return success ? Result.success(true) : Result.error("删除知识图谱失败");
    }

    /**
     * 删除指定节点及其相连的关系边
     */
    @OperationLog(type = OperationType.KG_DELETE_NODE, module = "KG",
            desc = "'删除知识节点: domain=' + #domainId + ' node=' + #nodeId",
            resourceId = "#domainId?.toString()")
    @DeleteMapping("/domain/{domainId}/node/{nodeId}")
    public Result<Boolean> deleteNode(@PathVariable Long domainId, @PathVariable String nodeId) {
        UserKnowledgeDomain domain = domainService.getById(domainId);
        if (domain == null) {
            return Result.error("领域不存在");
        }

        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> graphMap = (Map<String, Object>) domain.getGraphData();
            if (graphMap == null) {
                return Result.error("图谱数据为空");
            }

            List<Map<String, Object>> nodes = (List<Map<String, Object>>) graphMap.get("nodes");
            List<Map<String, Object>> edges = (List<Map<String, Object>>) graphMap.get("edges");

            if (nodes != null) {
                nodes.removeIf(node -> nodeId.equals(String.valueOf(node.get("id"))));
            }
            if (edges != null) {
                edges.removeIf(edge -> 
                    nodeId.equals(String.valueOf(edge.get("source"))) || 
                    nodeId.equals(String.valueOf(edge.get("target")))
                );
            }

            domain.setGraphData(graphMap);
            domain.setUpdatedAt(java.time.LocalDateTime.now());
            boolean success = domainService.updateById(domain);
            return success ? Result.success(true) : Result.error("节点删除失败");

        } catch (Exception e) {
            return Result.error("删除节点发生异常: " + e.getMessage());
        }
    }
}
