"""
RAG 多模态检索智能体 - 根据任务分解模块并发检索，根据用户画像调整召回策略
"""
import logging
import asyncio
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER, NODE_REVIEWER
from app.agents.llm_factory import get_rag_retriever_llm
from app.services.retrieval import HybridRetrievalService

logger = logging.getLogger("agents.rag_retriever")

_retrieval_service: HybridRetrievalService = None


def _get_retrieval_service() -> HybridRetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = HybridRetrievalService()
    return _retrieval_service


def _compute_retrieval_config(profile: Dict[str, Any]) -> Dict[str, Any]:
    """根据用户画像的 Felder-Silverman 模型决定检索策略"""
    behavior = profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})

    config = {
        "total_recall": 40,
        "rerank_top_n": 15,
        "image_bias": 0.5,
        "text_bias": 0.5,
    }

    vv = fs.get("visual_verbal", 0)
    config["image_bias"] = max(0.2, min(0.8, 0.5 - vv * 0.3))
    config["text_bias"] = 1.0 - config["image_bias"]

    si = fs.get("sensing_intuitive", 0)
    config["total_recall"] = int(40 + si * -10)
    config["total_recall"] = max(30, min(60, config["total_recall"]))
    config["rerank_top_n"] = max(10, min(30, config["total_recall"] // 3))

    logger.info(f"  [RAG检索] 检索配置: 召回={config['total_recall']}, 精排={config['rerank_top_n']}, 图片偏向={config['image_bias']:.2f}")
    return config


async def _retrieve_for_module(query: str, retrieval_config: Dict[str, Any]) -> Dict[str, Any]:
    """对单个模块执行检索"""
    service = _get_retrieval_service()
    result = await service.search(
        query=query,
        limit=retrieval_config["total_recall"],
        rerank_top_n=retrieval_config["rerank_top_n"],
    )
    return result


def _optimize_search_queries(modules: List[Dict[str, Any]], user_message: str, llm, chat_history: list = None) -> List[str]:
    """使用 LLM 为每个模块生成优化的检索词"""
    if not modules:
        logger.info(f"  [RAG检索] 无模块，使用用户消息作为查询")
        return [user_message]

    module_summaries = []
    for i, m in enumerate(modules):
        title = m.get("title", "")
        desc = m.get("description", "")
        kps = ", ".join(m.get("key_points", []))
        module_summaries.append(f"模块{i+1}: {title} - {desc} (要点: {kps})")

    logger.info(f"  [RAG检索] 正在优化 {len(modules)} 个模块的检索词...")

    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-6:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:150]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": """你是检索词优化专家。根据学习模块的描述和对话上下文，为每个模块生成最有效的搜索查询词。
严格输出 JSON 对象，格式如下：
{"queries": ["查询词1", "查询词2", "查询词3"]}
规则：
1. 查询词要精炼、具体，适合向量检索
2. 包含核心概念和关键词
3. 适合搜索教学资料
4. 结合对话历史理解用户的真实学习需求
5. queries 数组的元素个数必须与模块数相同
严禁使用 emoji。严禁输出 JSON 以外的任何内容。"""},
        {"role": "user", "content": f"""用户学习目标: {user_message}

对话历史（请结合上下文理解用户需求）:
{history_text if history_text else "无历史记录"}

学习模块（共{len(modules)}个）:
{chr(10).join(module_summaries)}

请为每个模块生成优化的检索查询词，严格输出 JSON 对象:"""}
    ]

    try:
        result = llm.chat_json(messages)
        if isinstance(result, dict) and "queries" in result:
            queries = result["queries"]
        elif isinstance(result, list):
            queries = result
        else:
            queries = [user_message]

        for i, q in enumerate(queries):
            logger.info(f"    查询{i+1}: {q}")
        return queries
    except Exception as e:
        logger.warning(f"  [RAG检索] 检索词优化失败: {str(e)}，使用模块标题降级")
        return [m.get("title", user_message) for m in modules] or [user_message]


def rag_retriever_node(state: AgentState) -> Dict[str, Any]:
    """RAG 多模态检索智能体节点"""
    user_message = state.get("user_message", "")
    task_breakdown = state.get("task_breakdown", {})
    user_profile = state.get("user_profile", {})
    modules = task_breakdown.get("modules", [])
    chat_history = state.get("chat_history", [])
    
    # 检查是否为重试模式（只检索指定模块）
    retry_mode = state.get("retry_mode", False)
    target_module_ids = state.get("target_module_ids", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [RAG检索智能体] 开始处理")
    logger.info(f"  用户输入: {user_message[:100]}")
    
    # 重试模式：只检索未通过的模块
    if retry_mode and target_module_ids:
        logger.info(f"  [RAG检索智能体] 🔄 重试模式：只检索模块 {target_module_ids}")
        
        # 筛选出需要重新检索的模块
        target_modules = []
        for module_id in target_module_ids:
            if 1 <= module_id <= len(modules):
                target_modules.append(modules[module_id - 1])
        
        if not target_modules:
            logger.warning(f"  [RAG检索智能体] 未找到目标模块，使用全部模块")
            target_modules = modules
        
        logger.info(f"  [RAG检索智能体] 待检索模块数: {len(target_modules)} (总共 {len(modules)} 个)")
        modules_to_retrieve = target_modules
    else:
        logger.info(f"  [RAG检索智能体] 待检索模块数: {len(modules)}")
        modules_to_retrieve = modules

    llm = get_rag_retriever_llm()
    retrieval_config = _compute_retrieval_config(user_profile)
    search_queries = _optimize_search_queries(modules_to_retrieve, user_message, llm, chat_history)

    all_results = []
    all_context_chunks = []

    async def run_retrievals():
        tasks = []
        for query in search_queries:
            tasks.append(_retrieve_for_module(query, retrieval_config))
        return await asyncio.gather(*tasks, return_exceptions=True)

    try:
        logger.info(f"  [RAG检索智能体] 正在并发执行 {len(search_queries)} 个检索任务...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_retrievals())
        loop.close()

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"    检索任务{i+1} 失败: {str(result)}")
                continue
            final_results = result.get("final_results", [])
            context_chunks = result.get("context_chunks", [])
            logger.info(f"    检索任务{i+1}: 召回 {len(final_results)} 条, 上下文 {len(context_chunks)} 块")
            all_results.extend(final_results)
            all_context_chunks.extend(context_chunks)

        # 去重
        seen_ids = set()
        deduped_results = []
        for r in all_results:
            rid = r.get("id")
            if rid not in seen_ids:
                seen_ids.add(rid)
                deduped_results.append(r)

        seen_content = set()
        deduped_chunks = []
        for chunk in all_context_chunks:
            content_key = chunk.get("content", "")[:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                deduped_chunks.append(chunk)

        rag_sufficient = len(deduped_chunks) > 0

        # 统计文本和图片数量
        text_count = sum(1 for c in deduped_chunks if c.get("type") == "text")
        image_count = sum(1 for c in deduped_chunks if c.get("type") == "image")

        logger.info(f"  [RAG检索智能体] 检索完成!")
        logger.info(f"    去重后结果: {len(deduped_results)} 条")
        logger.info(f"    上下文块: {len(deduped_chunks)} 个 (文本: {text_count}, 图片: {image_count})")
        logger.info(f"    检索充足: {'是' if rag_sufficient else '否'}")
        logger.info(f"{'='*60}")

        return {
            "search_queries": search_queries,
            "rag_results": deduped_results,
            "rag_context_chunks": deduped_chunks,
            "rag_sufficient": rag_sufficient,
            "retrieval_config": retrieval_config,
            "current_step": f"RAG检索智能体: 完成检索，共 {len(deduped_results)} 条结果，{len(deduped_chunks)} 个上下文块",
            "stream_events": [{
                "event_type": "search_results",
                "agent": "rag_retriever",
                "data": {
                    "queries": search_queries,
                    "total_results": len(deduped_results),
                    "total_chunks": len(deduped_chunks),
                    "config": retrieval_config,
                    "sufficient": rag_sufficient,
                },
                "step_description": f"检索完成，共召回 {len(deduped_results)} 条结果"
            }],
        }

    except Exception as e:
        logger.error(f"  [RAG检索智能体] 检索失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "rag_sufficient": False,
            "error": f"RAG 检索失败: {str(e)}",
            "current_step": f"RAG检索智能体: 检索失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "rag_retriever",
                "data": {"error": str(e)},
                "step_description": "检索失败"
            }],
        }
