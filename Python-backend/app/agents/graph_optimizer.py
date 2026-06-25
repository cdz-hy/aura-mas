import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.agents.llm_factory import get_knowledge_updater_llm

logger = logging.getLogger(__name__)

class GraphNode(BaseModel):
    id: str = Field(description="节点唯一标识，保留原ID或生成新的")
    name: str = Field(description="节点概念名称")
    description: str = Field(description="节点的简短定义")
    resource_ids: List[int] = Field(description="关联的资源ID列表，必须保留")
    mastery_level: float = Field(description="掌握度，必须严格继承原有节点的数据，如有合并可取平均值")
    importance: float = Field(description="重要性，0.1-1.0")

class GraphEdge(BaseModel):
    id: str = Field(description="关系边唯一标识")
    source: str = Field(description="源节点 ID")
    target: str = Field(description="目标节点 ID")
    relationship: str = Field(description="关系描述，使用简短纯中文词汇，如：包含、属于、支撑、依赖")

class GraphOutput(BaseModel):
    nodes: List[GraphNode] = Field(description="重构后的所有节点列表")
    edges: List[GraphEdge] = Field(description="重构后的所有边列表")

def optimize_graph(current_graph: Dict[str, Any], instruction: str, domain_name: str = "未知领域") -> Dict[str, Any]:
    """
    根据给定的指令，重新整理和优化完整的图谱数据。
    """
    llm = get_knowledge_updater_llm()
    
    current_graph_str = json.dumps(current_graph, ensure_ascii=False)
    schema_str = json.dumps(GraphOutput.model_json_schema(), ensure_ascii=False, indent=2)
    
    sys_prompt = f"""你是一个顶级的知识图谱架构专家。你需要基于现有的完整知识图谱 JSON（属于领域：【{domain_name}】），根据用户的【特定整理要求】，输出一份【全量重构后】的图谱数据。

【绝对强制约束】：
1. **数据继承**：在合并、保留或拆分节点时，你【必须】尽最大努力保留原有节点的 `mastery_level` (掌握度)、`importance` (重要性) 和 `resource_ids` 数据！如果你删除了某个旧节点并将概念合并到另一个节点，必须将它们的 resource_ids 合并。
2. **全量输出**：你输出的 JSON 将直接覆盖旧图谱。因此，你必须输出**完整**的 nodes 和 edges，如果某些节点没有被修改，也必须原封不动地包含在输出中。
3. **结构正确**：确保所有的 edges 中的 source 和 target 都存在于 nodes 列表中。去除悬空边。
4. **输出格式**：必须严格按照以下 JSON Schema 输出合法的 JSON 格式：
{schema_str}"""

    human_content = f"【当前完整图谱 JSON (领域: {domain_name})】:\n{current_graph_str}\n\n【用户的图谱整理要求】:\n{instruction}\n\n请严格遵守约束，执行整理，并严格按照上述 Schema 返回全新的完整图谱 JSON。"
    
    logger.info("开始调用大模型进行图谱智能整理...")
    
    try:
        # MIMOClient 使用 chat_json 返回字典
        result_dict = llm.chat_json([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": human_content}
        ])
        
        # 验证结构
        result = GraphOutput.model_validate(result_dict)
        
        # 转换为 Dict 格式
        new_graph = {
            "nodes": [n.model_dump() for n in result.nodes],
            "edges": [e.model_dump() for e in result.edges]
        }
        
        return new_graph
    except Exception as e:
        logger.error(f"图谱整理大模型调用失败: {e}")
        raise e
