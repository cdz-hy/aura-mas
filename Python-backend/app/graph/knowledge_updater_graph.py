import logging
import json
from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END

from app.agents.llm_factory import get_knowledge_updater_llm

from app.services.db.java_client import JavaBackendClient

logger = logging.getLogger("graph.knowledge_updater")
java_client = JavaBackendClient()

# 定义状态结构
class KnowledgeUpdaterState(TypedDict):
    user_id: int
    resource_id: int
    resource_text: str
    
    # 过程变量
    domain_name: Optional[str]
    domain_id: Optional[int]
    current_graph: Optional[Dict[str, Any]]
    
    # 输出变量
    new_graph: Optional[Dict[str, Any]]
    success: bool
    error: Optional[str]


# 节点 1: 领域分类 (Domain Classifier)
def classify_domain_node(state: KnowledgeUpdaterState):
    logger.info(f"开始为资源 {state['resource_id']} 进行领域分类...")
    llm = get_knowledge_updater_llm()
    
    # 获取用户现有的领域列表
    try:
        domains = java_client.get_user_knowledge_domains(state["user_id"])
        existing_domain_names = [d["domainName"] for d in domains] if domains else []
    except Exception as e:
        logger.warning(f"获取用户领域失败: {e}")
        existing_domain_names = []

    sys_msg = """你是一个智能分类助手。你需要根据用户提供的学习资源文本，判断它属于哪个宏观计算机科学或技术领域。
请输出最合适的领域名称，如"计算机网络", "操作系统", "机器学习", "前端开发"等。
如果资源内容可以归入以下用户已有的领域之一，请尽量使用该领域名称；否则，请输出一个全新的、概括性强的领域名称。
只需输出领域名称，不要有任何其他解释。"""

    human_content = f"【用户已有领域】: {', '.join(existing_domain_names)}\n【学习资源文本】:\n{state['resource_text'][:2000]}"
    
    resp_text = llm.chat([
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": human_content}
    ])
    domain_name = resp_text.strip()
    logger.info(f"分类结果: {domain_name}")
    
    # 匹配获取 domain_id
    domain_id = None
    if existing_domain_names and domain_name in existing_domain_names:
        for d in domains:
            if d["domainName"] == domain_name:
                domain_id = d["id"]
                break
                
    return {"domain_name": domain_name, "domain_id": domain_id}

# 节点 2: 图谱数据获取 (Graph Fetch)
def fetch_graph_node(state: KnowledgeUpdaterState):
    logger.info("获取当前领域图谱数据...")
    if state.get("domain_id"):
        try:
            domain = java_client.get_domain_knowledge_graph(state["domain_id"])
            graph_data = domain.get("graphData")
            if graph_data:
                return {"current_graph": graph_data}
        except Exception as e:
            logger.error(f"拉取图谱数据失败: {e}")
            
    # 如果没有 domain_id 或者拉取失败，初始化空图
    return {"current_graph": {"nodes": [], "edges": []}}

# 节点 3: 概念提取与融合 (Concept Extraction & Merge)
def extract_and_merge_node(state: KnowledgeUpdaterState):
    logger.info("提取概念并与现有图谱融合...")
    llm = get_knowledge_updater_llm()
    
    current_graph_str = json.dumps(state.get("current_graph", {"nodes": [], "edges": []}), ensure_ascii=False)
    
    sys_prompt = """你是一个顶级的知识图谱架构专家。你需要基于现有的知识图谱 JSON，从新的学习资源中提取【宏观层面的核心概念和关系】，并输出需要新增或更新的图谱数据。

【核心提取原则：控制粒度，拒绝琐碎】
1. **高度概括**：只提取该领域的“核心主题”、“关键技术”或“重要思想”（例如“微服务架构”、“深度学习”、“RESTful API”）。
2. **拒绝细枝末节**：坚决不要提取具体的函数名、参数、零散的代码细节、或者某本书的某个细微特性。
3. **合并抽象**：如果新内容只是现有概念的细微延伸或小例子，请不要创建新节点，而是直接将其忽略或归纳到现有的大概念中。
4. **数量克制**：对于单篇学习资源，新增节点数量建议控制在 3～6 个最核心的概念以内。保持图谱的清爽和宏观视角！

【节点规范】:
- id: 唯一标识 (例如 concept_1, concept_2)
- name: 概念名称 (必须是高度概括的名词或短语)
- description: 简短描述 (1-2句话概括该概念的核心定义)
- resource_ids: [资源ID数组]
- mastery_level: 固定为 0.0
- importance: 0.1 到 1.0 的浮点数，代表概念的基础性和重要性

【关系规范】:
- id: 唯一标识 (如 edge_1)
- source: 源节点 id
- target: 目标节点 id
- relationship: 关系类型 (必须使用简短的纯中文词汇，如：包含、属于、支撑、依赖、关联、组成、实现等)

【操作要求】:
1. 如果新提取的宏观概念在现有图谱中已存在（或含义高度相似），请不要修改其原有属性，仅在返回的节点列表中包含该节点，并确保其原有的 resource_ids 加上当前的【资源ID】。
2. 只有发现真正全新且足够重量级的核心概念时，才创建新节点。
3. 挖掘核心概念之间的逻辑联系，创建结构清晰的边。

【输出格式】:
为了避免输出过长，你**仅需返回需要新增或更新的内容（Patch）**。返回的 JSON 必须严格遵守以下格式，不要包裹 Markdown 标记（如 ```json）：
{
  "new_or_updated_nodes": [
    {
      "id": "concept_xxx", 
      "name": "...", 
      "description": "...", 
      "resource_ids": [...], 
      "mastery_level": 0.0, 
      "importance": 0.9
    }
  ],
  "new_edges": [
    {
      "id": "edge_xxx", 
      "source": "concept_a", 
      "target": "concept_b", 
      "relationship": "包含"
    }
  ]
}"""

    human_content = f"【当前图谱 JSON】:\n{current_graph_str}\n\n【当前资源ID】: {state['resource_id']}\n【学习资源文本】:\n{state['resource_text']}"
    
    try:
        patch_graph = llm.chat_json([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": human_content}
        ])
        
        # Programmatically merge patch_graph into current_graph
        current_graph = state.get("current_graph", {"nodes": [], "edges": []})
        nodes_dict = {n["id"]: n for n in current_graph.get("nodes", [])}
        edges_dict = {e["id"]: e for e in current_graph.get("edges", [])}
        
        for n in patch_graph.get("new_or_updated_nodes", []):
            if n["id"] in nodes_dict:
                # Merge resource_ids uniquely
                existing_rids = set(nodes_dict[n["id"]].get("resource_ids", []))
                existing_rids.update(n.get("resource_ids", []))
                nodes_dict[n["id"]]["resource_ids"] = list(existing_rids)
                # optionally update importance or description if AI provided better ones, but mainly just append resource_ids
            else:
                nodes_dict[n["id"]] = n
                
        for e in patch_graph.get("new_edges", []):
            edges_dict[e["id"]] = e
            
        new_graph = {
            "nodes": list(nodes_dict.values()),
            "edges": list(edges_dict.values())
        }
        
        return {"new_graph": new_graph, "success": True}
    except Exception as e:
        logger.error(f"解析大模型返回的图谱 JSON 失败: {e}")
        return {"error": "解析大模型图谱失败", "success": False}

# 节点 4: 持久化 (Persistence)
def persistence_node(state: KnowledgeUpdaterState):
    logger.info("持久化图谱数据到后端...")
    if not state.get("success"):
        logger.warning("合并步骤失败，跳过持久化。")
        return {}
        
    try:
        domain_id = state.get("domain_id")
        domain_name = state.get("domain_name")
        new_graph = state.get("new_graph")
        
        if domain_id:
            java_client.update_knowledge_domain(domain_id=domain_id, graph_data=new_graph)
        else:
            # 新建领域
            java_client.create_knowledge_domain(user_id=state["user_id"], domain_name=domain_name, graph_data=new_graph)
            
        logger.info("知识图谱持久化成功！")
        return {}
    except Exception as e:
        logger.error(f"持久化知识图谱异常: {e}")
        return {"error": str(e), "success": False}

# 构建图
def get_knowledge_updater_graph() -> StateGraph:
    workflow = StateGraph(KnowledgeUpdaterState)
    
    workflow.add_node("classify", classify_domain_node)
    workflow.add_node("fetch", fetch_graph_node)
    workflow.add_node("extract_merge", extract_and_merge_node)
    workflow.add_node("persist", persistence_node)
    
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "fetch")
    workflow.add_edge("fetch", "extract_merge")
    workflow.add_edge("extract_merge", "persist")
    workflow.add_edge("persist", END)
    
    return workflow.compile()
