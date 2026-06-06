"""
RAG 多模态检索智能体 - 根据任务分解模块并发检索，根据用户画像调整召回策略
"""
import logging
import asyncio
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_rag_retriever_llm
from app.prompts import RAG_RETRIEVER_QUERY_OPTIMIZER_PROMPT, RAG_RETRIEVER_CONFIG_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.services.retrieval import HybridRetrievalService

logger = logging.getLogger("agents.rag_retriever")

# rerank 相关性阈值：低于此分数的结果视为无关，直接过滤
RERANK_SCORE_THRESHOLD = 0.5

_retrieval_service: HybridRetrievalService = None


def _get_retrieval_service() -> HybridRetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = HybridRetrievalService()
    return _retrieval_service


async def _compute_retrieval_config(profile: Dict[str, Any], user_message: str, learning_goal: str, llm) -> Dict[str, Any]:
    """根据用户画像决定基线检索策略，并交由 LLM 结合上下文做最终调整"""
    import json
    behavior = profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})

    config = {
        "total_recall": 50,
        "rerank_top_n": 20,
        "image_bias": 0.5,
        "text_bias": 0.5,
        "min_rerank_score": RERANK_SCORE_THRESHOLD,
    }

    vv = fs.get("visual_verbal", 0)
    config["image_bias"] = max(0.2, min(0.8, 0.5 - vv * 0.3))
    config["text_bias"] = 1.0 - config["image_bias"]

    si = fs.get("sensing_intuitive", 0)
    config["total_recall"] = int(50 + si * -10)
    config["total_recall"] = max(30, min(70, config["total_recall"]))
    config["rerank_top_n"] = max(10, min(35, int(config["total_recall"] * 0.4)))

    baseline_image_limit = max(1, int(config["total_recall"] * config["image_bias"]))
    baseline_text_limit = max(1, int(config["total_recall"] * (1.0 - config["image_bias"])))
    logger.info(f"  [RAG检索] 基础配置基线: 召回={config['total_recall']} (图片: {baseline_image_limit}个, 文本: {baseline_text_limit}个), 精排={config['rerank_top_n']}, 图片偏向={config['image_bias']:.2f}")

    # 交由 LLM 动态决策
    try:
        prompt = RAG_RETRIEVER_CONFIG_PROMPT.format(
            learning_goal=learning_goal,
            user_message=user_message,
            baseline_recall=config["total_recall"],
            baseline_rerank=config["rerank_top_n"],
            baseline_image_bias=config["image_bias"]
        )
        messages = [{"role": "user", "content": prompt}]
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        
        # 提取 JSON
        if "{" in content and "}" in content:
            json_str = content[content.find("{"):content.rfind("}")+1]
            decision = json.loads(json_str)
            
            if "total_recall" in decision:
                config["total_recall"] = int(decision["total_recall"])
            if "rerank_top_n" in decision:
                config["rerank_top_n"] = int(decision["rerank_top_n"])
            if "image_bias" in decision:
                config["image_bias"] = float(decision["image_bias"])
                config["text_bias"] = 1.0 - config["image_bias"]
                
            image_limit = max(1, int(config["total_recall"] * config["image_bias"]))
            text_limit = max(1, int(config["total_recall"] * (1.0 - config["image_bias"])))
            logger.info(f"  [RAG检索] LLM自主调优后配置: 召回={config['total_recall']} (图片: {image_limit}个, 文本: {text_limit}个), 精排={config['rerank_top_n']}, 图片偏向={config['image_bias']:.2f}")
    except Exception as e:
        logger.warning(f"  [RAG检索] LLM 调优配置失败 ({e})，降级使用基线配置")

    # 最终计算并记录具体通道限制，存入配置字典中
    config["image_limit"] = max(1, int(config["total_recall"] * config["image_bias"]))
    config["text_limit"] = max(1, int(config["total_recall"] * (1.0 - config["image_bias"])))
    return config


async def _retrieve_for_module(query: str, retrieval_config: Dict[str, Any]) -> Dict[str, Any]:
    """对单个模块执行检索"""
    service = _get_retrieval_service()
    result = await service.search(
        query=query,
        limit=retrieval_config["total_recall"],
        rerank_top_n=retrieval_config["rerank_top_n"],
        min_rerank_score=retrieval_config.get("min_rerank_score", RERANK_SCORE_THRESHOLD),
        image_bias=retrieval_config.get("image_bias", 0.5)
    )
    return result


def _optimize_search_queries(
    modules: List[Dict[str, Any]],
    user_message: str,
    llm,
    chat_history: list = None,
    user_id: int = 0,
    task_id: int = None,
) -> List[str]:
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
        {"role": "system", "content": RAG_RETRIEVER_QUERY_OPTIMIZER_PROMPT},
        {"role": "user", "content": f"""用户学习目标: {user_message}

对话历史（请结合上下文理解用户需求）:
{history_text if history_text else "无历史记录"}

学习模块（共{len(modules)}个）:
{chr(10).join(module_summaries)}

请为每个模块生成优化的检索查询词，严格输出 JSON 对象:"""}
    ]

    try:
        result = llm.chat_json(messages)
        record_from_mimo(llm, user_id, "rag_query_optimization", task_id)
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


async def rag_retriever_node(state: AgentState) -> Dict[str, Any]:
    """RAG 多模态检索智能体节点"""
    user_message = state.get("user_message", "")
    task_breakdown = state.get("task_breakdown") or {}
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
        logger.info(f"  [RAG检索智能体] 重试模式：只检索模块 {target_module_ids}")
        
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

    retrieval_config = await _compute_retrieval_config(
        profile=user_profile,
        user_message=user_message,
        learning_goal=state.get("learning_goal", ""),
        llm=llm
    )
    
    # 获取各个模块的优化检索词
    search_queries = _optimize_search_queries(
        modules_to_retrieve,
        user_message,
        llm,
        chat_history,
        user_id=state.get("user_id", 0),
        task_id=state.get("task_id"),
    )

    all_results = []
    all_context_chunks = []
    poor_module_ids = []  # RAG 结果不足的模块 ID

    try:
        logger.info(f"  [RAG检索智能体] 正在并发执行 {len(search_queries)} 个检索任务...")
        tasks = []
        for query in search_queries:
            tasks.append(_retrieve_for_module(query, retrieval_config))
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            module_id = i + 1
            if isinstance(result, Exception):
                logger.error(f"    检索任务{i+1} 失败: {str(result)}")
                poor_module_ids.append(module_id)
                continue
            final_results = result.get("final_results", [])
            context_chunks = result.get("context_chunks", [])
            logger.info(f"    检索任务{i+1}: 召回 {len(final_results)} 条, 上下文 {len(context_chunks)} 块")

            # 检查单个模块的检索质量
            if not context_chunks:
                poor_module_ids.append(module_id)
                logger.warning(f"    模块{module_id} 无有效上下文，标记为需自主生成")
            else:
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

        # 统计文本和图片数量
        text_count = sum(1 for c in deduped_chunks if c.get("type") == "text")
        image_count = sum(1 for c in deduped_chunks if c.get("type") == "image")

        # 检索充足判断：过滤后仍有上下文块即为充足
        rag_sufficient = len(deduped_chunks) > 0

        logger.info(f"  [RAG检索智能体] 检索完成!")
        logger.info(f"    去重后结果: {len(deduped_results)} 条 (rerank 阈值: {RERANK_SCORE_THRESHOLD})")
        logger.info(f"    上下文块: {len(deduped_chunks)} 个 (文本: {text_count}, 图片: {image_count})")
        logger.info(f"    检索充足: {'是' if rag_sufficient else '否 (结果不足或均为低分无关内容)'}")
        if poor_module_ids:
            logger.info(f"    需自主生成的模块: {poor_module_ids}")

        # 自主异常检测：当所有模块检索结果都不足时，检查是否与目标根本偏离
        if (not state.get("background_generation")
                and not rag_sufficient
                and len(poor_module_ids) == len(modules_to_retrieve)
                and len(modules_to_retrieve) > 0):
            chunk_headings = []
            for c in deduped_chunks[:5]:
                h = " > ".join(c.get("heading", []))
                if h:
                    chunk_headings.append(h)
            anomaly_summary = f"检索目标: {user_message[:200]}; 检索到内容主题: {'; '.join(chunk_headings) if chunk_headings else '无有效结果'}"
            from app.agents.anomaly_checker import check_content_alignment
            is_aligned, anomaly_reason = check_content_alignment(user_message, anomaly_summary)
            if not is_aligned:
                logger.warning(f"  [RAG检索智能体] 自主检测到检索内容偏离: {anomaly_reason}")
                return {
                    "agent_anomaly": True,
                    "anomaly_reason": anomaly_reason,
                    "rag_sufficient": False,
                    "current_step": f"RAG检索智能体: 检测到检索偏离 - {anomaly_reason}",
                    "stream_events": [{
                        "event_type": "thinking",
                        "agent": "rag_retriever",
                        "data": {"message": f"检测到检索结果与目标偏离: {anomaly_reason}"},
                        "step_description": f"异常中断: {anomaly_reason}"
                    }],
                }

        logger.info(f"{'='*60}")

        return {
            "search_queries": search_queries,
            "rag_results": deduped_results,
            "rag_context_chunks": deduped_chunks,
            "rag_sufficient": rag_sufficient,
            "rag_poor_module_ids": poor_module_ids,
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
                    "poor_module_ids": poor_module_ids,
                },
                "step_description": f"检索完成，共召回 {len(deduped_results)} 条结果" + (f"，{len(poor_module_ids)} 个模块需自主生成" if poor_module_ids else "")
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
