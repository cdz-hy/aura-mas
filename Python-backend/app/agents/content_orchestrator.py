"""
内容编排智能体 - 将 RAG 检索结果规划排版为模块化的顺序合理、排版美观的多模态学习资源
采用 mimo-v2.5 标准模型（唯一使用标准模型的智能体）

优化策略：
- 支持并行编排模式：为每个模块并发调用 LLM 生成内容
- 支持批量编排模式：一次性生成所有模块（原有模式）
- 默认使用并行模式，提升性能和可靠性
"""
import logging
import json
import asyncio
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_content_orchestrator_llm
from app.prompts import CONTENT_ORCHESTRATOR_BATCH_PROMPT, CONTENT_ORCHESTRATOR_PARALLEL_PROMPT
from app.utils.token_recorder import record
from app.utils import stream_registry

VALID_MODULE_TYPES = {"text", "image", "diagram", "code", "summary", "mindmap"}


def _normalize_module_type(module_type: str) -> str:
    if not module_type:
        return "text"
    mt = module_type.strip().lower()
    return mt if mt in VALID_MODULE_TYPES else "text"


def _normalize_modules(modules: list) -> list:
    for m in modules:
        if "module_type" in m:
            m["module_type"] = _normalize_module_type(m["module_type"])
    return modules


def _emit(state: dict, event_type: str, content: str):
    """通过 sse_callback 实时推送 SSE 事件"""
    cb = state.get("sse_callback")
    if cb:
        try:
            cb(f'data: {json.dumps({"type": event_type, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass


def _emit_resource_stream(sse_callback, event_type: str, resource_id: int, content: str):
    """通过 sse_callback 推送带资源 ID 的流式事件"""
    if sse_callback:
        try:
            sse_callback(f'data: {json.dumps({"type": event_type, "resource_id": resource_id, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass


logger = logging.getLogger("agents.content_orchestrator")


def _flush_module_usage(modules_list: list, user_id: int, scene: str, task_id=None,
                         extra_records: list = None):
    """收集模块生成过程中的 token 消耗并统一记录"""
    all_records = list(extra_records or [])
    for m in modules_list:
        records = m.pop("_usage_records", None) or []
        all_records.extend(records)
    for rec in all_records:
        record(
            user_id=user_id,
            scene=scene,
            model_name=rec["model"],
            input_tokens=rec["input_tokens"],
            output_tokens=rec["output_tokens"],
            task_id=task_id,
        )

def _get_personalized_preferences(user_profile: Dict[str, Any]) -> str:
    """根据用户画像中的 Felder-Silverman 学习风格计算个性化编排要求"""
    behavior = user_profile.get("learning_behavior", {})
    vv = behavior.get("visual_vs_verbal", 0.0)
    si = behavior.get("sensing_vs_intuitive", 0.0)

    # 1. 详细度与文本长度偏好 (Sensing vs Intuitive)
    if si < -0.3:
        detail_pref = "详细度极高！必须尽可能输出极长且内容极度丰富的文本。提供极其详尽、具体的概念深度剖析、海量实例应用和事无巨细的步骤拆解，切勿精简任何细节，字数越多越好！"
    elif si > 0.3:
        detail_pref = "偏好高层概念和原理解释。核心理论讲解需尽量丰富透彻，输出较长的篇幅以确保原理解释的深度，但在举例说明时可适当保持精炼，避免过于碎片化的细节，但总体篇幅仍需保持较长且充实。"
    else:
        detail_pref = "详细度高，需要输出较长篇幅的文本。提供丰富的理论说明与充实的实例分析，请放开字数限制，尽可能详尽地展开讲解。"

    # 2. 图片数量与图文配比偏好 (Visual vs Verbal)
    if vv <= -0.8:
        image_pref = "极度偏好视觉学习。1. 必须积极且合理地将上下文中提供的所有相关的真实图片嵌入内容中。2. 请极其频繁地自主生成能够提纲挈领的 Mermaid 各种图表（flowchart、sequenceDiagram、mindmap等）来直观展现知识点逻辑。注意：必须确保内容有意义需要时才生成，严禁胡编乱造事实，必须基于提供的RAG文本或网络资源生成，且必须严格遵循 Mermaid 语法。"
    elif vv <= -0.4:
        image_pref = "强偏好视觉。1. 必须积极且合理地将上下文中提供的相关的真实图片嵌入内容中。2. 对于关键且复杂的概念，请较常地自主生成一些 Mermaid 图表（如 flowchart）来辅助说明。注意：必须有必要且有意义时才生成，严禁胡编乱造，必须基于检索资源生成，严格遵循 Mermaid 语法。"
    elif vv < 0:
        image_pref = "轻微偏好视觉。正常搭配真实图片。当内容极度复杂且确有必要时，偶尔可以选择性地自主生成少量的 Mermaid 流程图（flowchart）辅助说明。严禁胡编乱造，严格遵循 Mermaid 语法。"
    elif vv > 0.3:
        image_pref = "强偏好纯文字与逻辑表述。尽量少用图片（每个模块最多 1 张，无核心图则不用）。严禁自主生成任何 Mermaid 图表。"
    else:
        image_pref = "图文平衡。根据内容自然搭配图片（1-2 张）。除非极度必要，否则不要自主生成 Mermaid 图表。"

    return (
        f"1. 详细度与篇幅：{detail_pref}\n"
        f"2. 图文配比与图片数量：{image_pref}"
    )


def _generate_single_module(
    module_info: Dict[str, Any],
    module_order: int,
    rag_chunks: List[Dict[str, Any]],
    user_profile: Dict[str, Any],
    learning_goal: str,
    chat_history: List[Dict[str, str]],
    sse_callback=None,
    resource_id: int = 0,
) -> Dict[str, Any]:
    """
    为单个模块生成内容（用于并行编排）
    
    Args:
        module_info: 模块信息（来自任务分解）
        module_order: 模块顺序
        rag_chunks: RAG 检索到的内容块
        user_profile: 用户画像
        learning_goal: 学习目标
        chat_history: 对话历史
    
    Returns:
        生成的模块内容
    """
    llm = get_content_orchestrator_llm()
    
    module_title = module_info.get("title", "")
    module_desc = module_info.get("description", "")
    key_points = module_info.get("key_points", [])
    
    # 筛选与该模块相关的 RAG 内容
    relevant_chunks = []
    for chunk in rag_chunks:
        chunk_content = chunk.get("content", "").lower()
        doc_title = chunk.get("doc_title", "").lower()
        heading = " ".join(chunk.get("heading", [])).lower()
        
        # 简单的相关性判断：标题或关键点在内容中出现
        is_relevant = (
            module_title.lower() in chunk_content or
            module_title.lower() in doc_title or
            module_title.lower() in heading or
            any(kp.lower() in chunk_content for kp in key_points)
        )
        
        if is_relevant:
            relevant_chunks.append(chunk)
    
    # 如果没有相关内容，使用前 5 个通用内容
    if not relevant_chunks:
        relevant_chunks = rag_chunks[:5]
    
    # 构造内容摘要
    content_parts = []
    for i, chunk in enumerate(relevant_chunks[:10]):
        chunk_type = chunk.get("type", "text")
        heading = " > ".join(chunk.get("heading", []))
        doc_title = chunk.get("doc_title", "")
        if chunk_type == "image":
            content_parts.append(
                f"[资料{i+1}] [图片] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"图片URL: {chunk.get('image_path', '')}\n"
                f"AI描述: {chunk.get('image_caption', '')}\n"
                f"上下文: {chunk.get('content', '')}"
            )
        else:
            content_parts.append(
                f"[资料{i+1}] [文本] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"内容: {chunk.get('content', '')}"
            )
    
    content_text = "\n\n---\n\n".join(content_parts)
    
    # 用户偏好
    user_pref_text = _get_personalized_preferences(user_profile)
    logger.info(f"  [模块{module_order}] 编排个性化偏好约束:\n{user_pref_text}")

    
    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-4:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:150]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)
    
    # 获取资源类型（如果指定了特定类型，强制使用）
    resource_types = module_info.get("resources", [])
    forced_type = resource_types[0].get("resource_type", "") if resource_types else ""

    type_hint = ""
    if forced_type:
        type_hint = f"- 指定资源类型: {forced_type}（必须使用此类型作为 module_type）\n"
        if forced_type == "mindmap":
            type_hint += "- 重要: 必须输出 MindElixir nodeData JSON 格式，详见系统提示\n"

    messages = [
        {"role": "system", "content": CONTENT_ORCHESTRATOR_PARALLEL_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

对话历史:
{history_text if history_text else "无历史记录"}

当前模块信息:
- 标题: {module_title}
- 描述: {module_desc}
- 关键要点: {', '.join(key_points)}
- 模块顺序: 第 {module_order} 个模块
{type_hint}
用户个性化内容偏好要求（必须严格遵守且在此模块中体现）:
{user_pref_text}

检索到的相关知识资料:
{content_text}

请为该模块生成高质量的学习内容，输出 JSON:"""}
    ]
    
    try:
        def _on_chunk(chunk: str):
            _emit_resource_stream(sse_callback, "resource_stream_text", resource_id, chunk)

        result = llm.chat_json_stream(messages, on_chunk=_on_chunk, max_tokens=16384, stream_field="content")
        result["module_order"] = module_order
        result["module_id"] = module_info.get("module_id", module_order)
        result["_usage_records"] = llm.get_usage_records()
        return result
    except Exception as e:
        logger.error(f"  [模块{module_order}] 生成失败: {str(e)}")
        return {
            "module_order": module_order,
            "module_id": module_info.get("module_id", module_order),
            "module_type": "text",
            "title": module_title,
            "content": f"内容生成失败: {str(e)}",
            "description": module_desc,
            "metadata": {"error": str(e)},
        }


async def content_orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """
    内容编排智能体节点
    
    支持两种模式：
    1. 并行模式（默认）：为每个模块并发调用 LLM 生成内容
    2. 批量模式：一次性生成所有模块（原有模式）
    
    支持重试模式：
    - 只重新生成未通过审查的模块
    - 保留已通过审查的模块
    - 合并新旧模块结果
    
    并行模式优势：
    - 更快的响应速度（并发执行）
    - 更好的容错性（单个模块失败不影响其他）
    - 更好的流式体验（逐个模块实时输出）
    - 无 token 限制（每个模块独立生成）
    """
    rag_chunks = state.get("rag_context_chunks", [])
    task_breakdown = state.get("task_breakdown") or {}
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    user_profile = state.get("user_profile", {})
    generated_content = state.get("generated_content")
    chat_history = state.get("chat_history", [])
    session_id = state.get("session_id", "")

    # 是否使用并行模式（默认开启）
    use_parallel = state.get("use_parallel_orchestration", True)

    # 检查是否为重试模式（只重新生成指定模块）
    retry_mode = state.get("retry_mode", False)
    target_module_ids = state.get("target_module_ids", [])
    existing_modules = state.get("module_list", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [内容编排智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    logger.info(f"  输入内容块: {len(rag_chunks)} 个")
    logger.info(f"  自主生成内容: {'有' if generated_content else '无'}")
    logger.info(f"  编排模式: {'并行' if use_parallel else '批量'}")
    
    modules = task_breakdown.get("modules", []) if task_breakdown else []
    
    # 重试模式：只重新生成未通过的模块
    if retry_mode and target_module_ids and existing_modules:
        logger.info(f"  [内容编排智能体] 🔄 重试模式：只重新生成模块 {target_module_ids}")
        logger.info(f"  [内容编排智能体] 保留已通过的 {len(existing_modules) - len(target_module_ids)} 个模块")
        
        # 筛选出需要重新生成的模块信息
        target_modules_info = []
        for module_id in target_module_ids:
            if 1 <= module_id <= len(modules):
                module_info = modules[module_id - 1]
                target_modules_info.append((module_id, module_info))
        
        if not target_modules_info:
            logger.warning(f"  [内容编排智能体] 未找到目标模块信息，跳过重试")
            return {
                "retry_mode": False,
                "target_module_ids": [],
                "current_step": "内容编排智能体: 未找到目标模块，跳过重试",
            }
        
        # 如果有自主生成内容，添加到 RAG 结果中
        if generated_content:
            rag_chunks = list(rag_chunks)
            rag_chunks.append({
                "type": "text",
                "content": generated_content.get("content", ""),
                "doc_title": "自主生成内容",
                "heading": [generated_content.get("title", "补充内容")],
            })
        
        # 并发重新生成未通过的模块
        # 优先从 state 获取回调；回退到 stream_registry（checkpointer 序列化会丢失 callable）
        sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(session_id)
        placeholder_map = state.get("placeholder_resource_map") or stream_registry.get_placeholder_map(session_id)

        try:
            tasks = []
            for module_id, module_info in target_modules_info:
                placeholder = placeholder_map.get(module_id, {})
                res_id = placeholder.get("id", 0)
                task = asyncio.to_thread(
                    _generate_single_module,
                    module_info,
                    module_id,
                    rag_chunks,
                    user_profile,
                    learning_goal,
                    chat_history,
                    sse_cb,
                    res_id,
                )
                tasks.append(task)
            
            # 并发执行所有任务 (直接 await)
            new_module_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            new_modules = []
            for i, result in enumerate(new_module_results):
                module_id = target_modules_info[i][0]
                if isinstance(result, Exception):
                    logger.error(f"  [模块{module_id}] 重新生成异常: {str(result)}")
                    # 保留原有模块
                    original_module = existing_modules[module_id - 1] if module_id <= len(existing_modules) else None
                    if original_module:
                        new_modules.append(original_module)
                else:
                    new_modules.append(result)
            
            # 合并结果：保留通过的模块，替换未通过的模块
            final_modules = _merge_modules(existing_modules, new_modules, target_module_ids)
            
            # 按 module_order 排序
            final_modules.sort(key=lambda x: x.get("module_order", 0))
            _normalize_modules(final_modules)

            # 构造完整结果
            orchestrated_content = {
                "title": task_breakdown.get("title", learning_goal),
                "description": task_breakdown.get("description", ""),
                "modules": final_modules,
                "total_modules": len(final_modules),
                "summary": f"已重新生成 {len(new_modules)} 个模块，保留 {len(final_modules) - len(new_modules)} 个模块",
            }
            
            logger.info(f"  [内容编排智能体] 重试编排完成!")
            logger.info(f"    重新生成: {len(new_modules)} 个模块")
            logger.info(f"    保留原有: {len(final_modules) - len(new_modules)} 个模块")
            logger.info(f"    总模块数: {len(final_modules)}")
            for i, m in enumerate(final_modules):
                mtype = m.get("module_type", "text")
                mtitle = m.get("title", "")
                module_order = m.get("module_order", i + 1)
                is_new = module_order in target_module_ids
                status = " 重新生成" if is_new else " 保留"
                logger.info(f"      模块{module_order} [{mtype}] {status}: {mtitle}")
            logger.info(f"{'='*60}")
            
            _flush_module_usage(new_modules, state.get("user_id", 0),
                                "content_orchestration", state.get("task_id"))

            # 自主异常检测：重试模式下检查编排内容是否偏离
            content_previews = []
            for m in final_modules[:3]:
                c = m.get("content", "")
                if isinstance(c, str):
                    content_previews.append(f"{m.get('title', '')}: {c[:120]}")
            if content_previews:
                from app.agents.anomaly_checker import check_content_alignment
                is_aligned, anomaly_reason = check_content_alignment(
                    learning_goal, "重试编排模块: " + "; ".join(content_previews),
                    state.get("user_id", 0), state.get("task_id")
                )
                if not is_aligned:
                    logger.warning(f"  [内容编排智能体] 重试编排检测到内容偏离: {anomaly_reason}")
                    return {
                        "agent_anomaly": True,
                        "anomaly_reason": anomaly_reason,
                        "module_list": final_modules,
                        "orchestrated_content": orchestrated_content,
                        "current_step": f"内容编排智能体: 重试编排检测到内容偏离 - {anomaly_reason}",
                        "stream_events": [{
                            "event_type": "thinking",
                            "agent": "content_orchestrator",
                            "data": {"message": f"检测到编排内容与目标偏离: {anomaly_reason}"},
                            "step_description": f"异常中断: {anomaly_reason}"
                        }],
                    }

            return {
                "orchestrated_content": orchestrated_content,
                "module_list": final_modules,
                "retry_mode": False,  # 清除重试标记
                "target_module_ids": [],
                "current_step": f"内容编排智能体: 重试编排完成，重新生成 {len(new_modules)} 个模块",
                "stream_events": [{
                    "event_type": "module",
                    "agent": "content_orchestrator",
                    "data": orchestrated_content,
                    "step_description": f"重试编排完成，重新生成 {len(new_modules)} 个模块"
                }],
            }
            
        except Exception as e:
            logger.error(f"  [内容编排智能体] 重试编排失败: {str(e)}")
            # 保留原有模块
            return {
                "retry_mode": False,
                "target_module_ids": [],
                "error": f"重试编排失败: {str(e)}",
                "current_step": f"内容编排智能体: 重试编排失败 - {str(e)}",
            }
    
    # 如果有自主生成内容，添加到 RAG 结果中
    if generated_content:
        rag_chunks = list(rag_chunks)
        rag_chunks.append({
            "type": "text",
            "content": generated_content.get("content", ""),
            "doc_title": "自主生成内容",
            "heading": [generated_content.get("title", "补充内容")],
        })
    
    # 并行模式：为每个模块并发生成内容
    if use_parallel and modules:
        logger.info(f"  [内容编排智能体] 使用并行模式，共 {len(modules)} 个模块")
        _emit(state, "progress", f"正在并行编排 {len(modules)} 个学习模块...")
        # 优先从 state 获取回调；回退到 stream_registry（checkpointer 序列化会丢失 callable）
        sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(session_id)
        placeholder_map = state.get("placeholder_resource_map") or stream_registry.get_placeholder_map(session_id)

        # 单模块自动确认场景：placeholder_resource_map 为空，通过回调动态创建
        if not placeholder_map and modules:
            create_placeholder_cb = state.get("create_placeholder_callback") or stream_registry.get_create_placeholder_callback(session_id)
            if create_placeholder_cb:
                try:
                    placeholder_map = create_placeholder_cb(modules)
                    stream_registry.update_placeholder_map(session_id, placeholder_map)
                except Exception as e:
                    logger.warning(f"  [内容编排智能体] 创建占位资源失败: {e}")

        # 通知前端创建侧栏占位条目
        if placeholder_map:
            logger.info(f"  [内容编排智能体] 发送 resource_stream_start，共 {len(placeholder_map)} 个占位")
            _emit(state, "resource_stream_start", json.dumps(list(placeholder_map.values()), ensure_ascii=False))
            # 若 state 中无 sse_callback，直接通过 sse_cb 推送（state._emit 依赖 state["sse_callback"]）
            if not state.get("sse_callback") and sse_cb:
                try:
                    sse_cb(f'data: {json.dumps({"type": "resource_stream_start", "content": json.dumps(list(placeholder_map.values()), ensure_ascii=False)}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        try:
            tasks = []
            for i, module in enumerate(modules):
                module_order = i + 1
                placeholder = placeholder_map.get(module_order, {})
                res_id = placeholder.get("id", 0)
                task = asyncio.to_thread(
                    _generate_single_module,
                    module,
                    module_order,
                    rag_chunks,
                    user_profile,
                    learning_goal,
                    chat_history,
                    sse_cb,
                    res_id,
                )
                tasks.append(task)
            
            # 并发执行所有任务 (直接 await)
            module_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            modules_list = []
            for i, result in enumerate(module_results):
                if isinstance(result, Exception):
                    logger.error(f"  [模块{i+1}] 生成异常: {str(result)}")
                    modules_list.append({
                        "module_order": i + 1,
                        "module_type": "text",
                        "title": modules[i].get("title", f"模块 {i+1}"),
                        "content": f"内容生成失败: {str(result)}",
                        "metadata": {"error": str(result)},
                    })
                else:
                    modules_list.append(result)
            
            # 按 module_order 排序
            modules_list.sort(key=lambda x: x.get("module_order", 0))
            _normalize_modules(modules_list)

            # 构造完整结果
            orchestrated_content = {
                "title": task_breakdown.get("title", learning_goal),
                "description": task_breakdown.get("description", ""),
                "modules": modules_list,
                "total_modules": len(modules_list),
                "summary": f"已生成 {len(modules_list)} 个学习模块",
            }
            
            _emit(state, "progress", f"并行编排完成，共生成 {len(modules_list)} 个学习模块")
            logger.info(f"  [内容编排智能体] 并行编排完成!")
            logger.info(f"    标题: {orchestrated_content.get('title', '未命名')}")
            logger.info(f"    模块数: {len(modules_list)}")
            for i, m in enumerate(modules_list):
                mtype = m.get("module_type", "text")
                mtitle = m.get("title", "")
                concepts = m.get("metadata", {}).get("key_concepts", [])
                has_error = "error" in m.get("metadata", {})
                status = " 失败" if has_error else " 成功"
                logger.info(f"      模块{i+1} [{mtype}] {status}: {mtitle} (概念: {', '.join(concepts[:3])})")
            logger.info(f"{'='*60}")
            
            _flush_module_usage(modules_list, state.get("user_id", 0),
                                "content_orchestration", state.get("task_id"))

            # 自主异常检测：检查编排内容是否与学习目标偏离
            content_previews = []
            for m in modules_list[:3]:
                c = m.get("content", "")
                if isinstance(c, str):
                    content_previews.append(f"{m.get('title', '')}: {c[:120]}")
            if content_previews:
                from app.agents.anomaly_checker import check_content_alignment
                is_aligned, anomaly_reason = check_content_alignment(
                    learning_goal, "编排模块: " + "; ".join(content_previews),
                    state.get("user_id", 0), state.get("task_id")
                )
                if not is_aligned:
                    logger.warning(f"  [内容编排智能体] 检测到编排内容偏离: {anomaly_reason}")
                    return {
                        "agent_anomaly": True,
                        "anomaly_reason": anomaly_reason,
                        "module_list": modules_list,
                        "orchestrated_content": orchestrated_content,
                        "current_step": f"内容编排智能体: 检测到内容偏离 - {anomaly_reason}",
                        "stream_events": [{
                            "event_type": "thinking",
                            "agent": "content_orchestrator",
                            "data": {"message": f"检测到编排内容与目标偏离: {anomaly_reason}"},
                            "step_description": f"异常中断: {anomaly_reason}"
                        }],
                    }

            return {
                "orchestrated_content": orchestrated_content,
                "module_list": modules_list,
                "current_step": f"内容编排智能体: 并行编排完成，共 {len(modules_list)} 个模块",
                "stream_events": [{
                    "event_type": "module",
                    "agent": "content_orchestrator",
                    "data": orchestrated_content,
                    "step_description": f"并行编排完成，共 {len(modules_list)} 个模块"
                }],
            }
            
        except Exception as e:
            logger.error(f"  [内容编排智能体] 并行编排失败: {str(e)}")
            # 降级到批量模式
            logger.warning(f"  [内容编排智能体] 降级到批量模式")
            use_parallel = False
    
    # 批量模式：一次性生成所有模块（原有逻辑）
    if not use_parallel or not modules:
        logger.info(f"  [内容编排智能体] 使用批量模式")
        _emit(state, "progress", "正在编排学习内容...")
        batch_result = _batch_orchestration(
            rag_chunks, task_breakdown, user_message, learning_goal,
            user_profile, generated_content, chat_history,
            sse_callback=state.get("sse_callback"),
        )
        extra_records = batch_result.pop("_usage_records", None) or []
        _flush_module_usage(batch_result.get("module_list", []),
                            state.get("user_id", 0),
                            "content_orchestration", state.get("task_id"),
                            extra_records=extra_records)

        # 自主异常检测：批量模式
        batch_modules = batch_result.get("module_list", [])
        content_previews = []
        for m in batch_modules[:3]:
            c = m.get("content", "")
            if isinstance(c, str):
                content_previews.append(f"{m.get('title', '')}: {c[:120]}")
        if content_previews:
            from app.agents.anomaly_checker import check_content_alignment
            is_aligned, anomaly_reason = check_content_alignment(
                learning_goal, "批量编排模块: " + "; ".join(content_previews),
                state.get("user_id", 0), state.get("task_id")
            )
            if not is_aligned:
                logger.warning(f"  [内容编排智能体] 批量编排检测到内容偏离: {anomaly_reason}")
                return {
                    "agent_anomaly": True,
                    "anomaly_reason": anomaly_reason,
                    "module_list": batch_modules,
                    "orchestrated_content": batch_result.get("orchestrated_content"),
                    "current_step": f"内容编排智能体: 批量编排检测到内容偏离 - {anomaly_reason}",
                    "stream_events": [{
                        "event_type": "thinking",
                        "agent": "content_orchestrator",
                        "data": {"message": f"检测到编排内容与目标偏离: {anomaly_reason}"},
                        "step_description": f"异常中断: {anomaly_reason}"
                    }],
                }

        return batch_result


def _batch_orchestration(
    rag_chunks: List[Dict[str, Any]],
    task_breakdown: Dict[str, Any],
    user_message: str,
    learning_goal: str,
    user_profile: Dict[str, Any],
    generated_content: Dict[str, Any],
    chat_history: List[Dict[str, str]],
    sse_callback=None,
) -> Dict[str, Any]:
    """批量编排模式：一次性生成所有模块（原有逻辑）"""
    llm = get_content_orchestrator_llm()

    content_parts = []
    for i, chunk in enumerate(rag_chunks[:20]):
        chunk_type = chunk.get("type", "text")
        heading = " > ".join(chunk.get("heading", []))
        doc_title = chunk.get("doc_title", "")
        if chunk_type == "image":
            content_parts.append(
                f"[资料{i+1}] [图片] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"图片URL: {chunk.get('image_path', '')}\n"
                f"AI描述: {chunk.get('image_caption', '')}\n"
                f"上下文: {chunk.get('content', '')}"
            )
        else:
            content_parts.append(
                f"[资料{i+1}] [文本] 来源: {doc_title}\n"
                f"章节: {heading}\n"
                f"内容: {chunk.get('content', '')}"
            )

    content_text = "\n\n---\n\n".join(content_parts)

    generated_text = ""
    if generated_content:
        generated_text = f"\n\n## 自主生成的补充内容:\n{generated_content.get('content', '')}"

    modules_desc = ""
    if task_breakdown:
        modules = task_breakdown.get("modules", [])
        desc_lines = []
        for i, m in enumerate(modules):
            line = f"- 模块{m.get('module_id', i+1)}: {m.get('title', '')} - {m.get('description', '')}"
            resources = m.get("resources", [])
            if resources:
                types = [r.get("resource_type", "") for r in resources if r.get("resource_type")]
                if types:
                    line += f" [指定类型: {', '.join(types)}]"
            desc_lines.append(line)
        modules_desc = "\n".join(desc_lines)

    user_pref_text = _get_personalized_preferences(user_profile)
    logger.info(f"  [内容编排] 批量编排启动，用户画像偏好要求:\n{user_pref_text}")


    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-6:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": CONTENT_ORCHESTRATOR_BATCH_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

对话历史（请结合上下文理解用户需求）:
{history_text if history_text else "无历史记录"}

参考学习路径:
{modules_desc}

用户个性化内容偏好要求（必须严格遵守且在生成的各个模块中体现）:
{user_pref_text}

检索到的知识资料:
{content_text}
{generated_text}

请将以上资料编排为结构化的学习资源，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [内容编排智能体] 正在调用 LLM 进行批量编排...")
        result = llm.chat_json(messages, max_tokens=16384)
        modules_list = result.get("modules", [])
        _normalize_modules(modules_list)

        logger.info(f"  [内容编排智能体] 批量编排完成!")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    模块数: {len(modules_list)}")
        for i, m in enumerate(modules_list):
            mtype = m.get("module_type", "text")
            mtitle = m.get("title", "")
            concepts = m.get("metadata", {}).get("key_concepts", [])
            logger.info(f"      模块{i+1} [{mtype}]: {mtitle} (概念: {', '.join(concepts[:3])})")
        logger.info(f"{'='*60}")

        return {
            "orchestrated_content": result,
            "module_list": modules_list,
            "_usage_records": llm.get_usage_records(),
            "current_step": f"内容编排智能体: 批量编排完成，共 {len(modules_list)} 个模块",
            "stream_events": [{
                "event_type": "module",
                "agent": "content_orchestrator",
                "data": result,
                "step_description": f"批量编排完成，共 {len(modules_list)} 个模块"
            }],
        }

    except Exception as e:
        logger.error(f"  [内容编排智能体] 批量编排失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"内容编排失败: {str(e)}",
            "current_step": f"内容编排智能体: 编排失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "content_orchestrator",
                "data": {"error": str(e)},
                "step_description": "内容编排失败"
            }],
        }


def _merge_modules(
    existing_modules: List[Dict[str, Any]],
    new_modules: List[Dict[str, Any]],
    target_module_ids: List[int],
) -> List[Dict[str, Any]]:
    """
    合并模块结果：保留通过的模块，替换未通过的模块
    
    Args:
        existing_modules: 原有的所有模块
        new_modules: 新生成的模块（只包含需要替换的）
        target_module_ids: 需要替换的模块编号列表
    
    Returns:
        合并后的完整模块列表
    """
    # 创建新模块的映射表（module_order -> module）
    new_modules_map = {}
    for module in new_modules:
        module_order = module.get("module_order", 0)
        new_modules_map[module_order] = module
    
    # 合并结果
    final_modules = []
    for i, existing_module in enumerate(existing_modules):
        module_order = existing_module.get("module_order", i + 1)
        
        # 如果该模块需要替换且有新生成的版本，使用新版本
        if module_order in target_module_ids and module_order in new_modules_map:
            final_modules.append(new_modules_map[module_order])
            logger.info(f"    [合并] 模块{module_order}: 使用新生成版本")
        else:
            # 否则保留原有版本
            final_modules.append(existing_module)
            logger.info(f"    [合并] 模块{module_order}: 保留原有版本")
    
    return final_modules
