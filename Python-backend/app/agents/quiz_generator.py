"""
题目生成智能体 - 结合用户画像中的薄弱点和偏好题型，自主抉择题目类型并生成题目
可选择调用 RAG 检索相关知识点结合内容生成
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_quiz_generator_llm
from app.prompts import QUIZ_GENERATOR_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.utils import stream_registry
import json

logger = logging.getLogger("agents.quiz_generator")



def quiz_generator_node(state: AgentState) -> Dict[str, Any]:
    """题目生成智能体节点"""
    user_message = state.get("user_message", "")
    current_module_title = state.get("current_module_title", "")
    learning_goal = state.get("learning_goal", user_message)

    # 优先使用当前选择的模块标题作为出题目标
    quiz_target = current_module_title if current_module_title else learning_goal

    rag_chunks = state.get("rag_context_chunks", [])
    user_profile = state.get("user_profile", {})
    orchestrated_content = state.get("orchestrated_content")
    source_resource_content = state.get("source_resource_content", "")
    chat_history = state.get("chat_history", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [题目生成智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")

    # 实时推送思考过程
    _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))

    def _emit_thinking(content: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "题目生成智能体", "content": content}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_start(agent: str, prefix: str = ""):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_start", "agent": agent, "content": prefix}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    def _emit_thinking_chunk(chunk: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking_chunk", "content": chunk}, ensure_ascii=False)}\n\n')
            except Exception:
                pass

    llm = get_quiz_generator_llm()

    behavior = user_profile.get("learning_behavior", {})
    weak_points = behavior.get("weak_areas", [])
    pref_types = behavior.get("preferred_quiz_types", [])
    pref_quiz_pref = behavior.get("preferred_quiz_preference", {})

    if weak_points:
        logger.info(f"  [题目生成智能体] 用户薄弱点: {', '.join(weak_points)}")
    if pref_types:
        logger.info(f"  [题目生成智能体] 偏好题型: {', '.join(pref_types)}")

    content_summary = ""
    if source_resource_content:
        content_summary = source_resource_content
        logger.info(f"  [题目生成智能体] 使用选择的源资源内容作为出题上下文 ({len(source_resource_content)} 字符)")
    elif orchestrated_content:
        modules = orchestrated_content.get("modules", [])
        content_summary = "\n".join([
            f"模块{i+1} - {m.get('title', '')}: {m.get('content', '')[:200]}"
            for i, m in enumerate(modules[:5])
        ])
        logger.info(f"  [题目生成智能体] 使用编排内容: {len(modules)} 个模块")
    elif rag_chunks:
        content_summary = "\n".join([
            f"[{i+1}] {c.get('content', '')[:200]}"
            for i, c in enumerate(rag_chunks[:8])
        ])
        logger.info(f"  [题目生成智能体] 使用 RAG 检索内容: {len(rag_chunks)} 块")

    # 题目偏好上下文构建
    pref_quiz_text = ""
    if isinstance(pref_quiz_pref, dict) and pref_quiz_pref:
        pref_types_list = pref_quiz_pref.get("types") or pref_types
        pref_count = pref_quiz_pref.get("count")
        pref_diff = pref_quiz_pref.get("difficulty")
        pref_quiz_text = f"""已有的偏好题目配置:
- 偏好题型: {', '.join(pref_types_list) if pref_types_list else '暂无'}
- 偏好题目数量: {f"{pref_count}道" if pref_count else '暂无'}
- 偏好难度: {pref_diff if pref_diff else '暂无'}"""
    else:
        pref_quiz_text = f"已有的偏好题型: {', '.join(pref_types) if pref_types else '暂无'}"

    weak_text = f"薄弱知识点: {', '.join(weak_points)}" if weak_points else "暂无薄弱点记录"

    # 构造对话历史上下文
    history_text = ""
    if chat_history:
        recent = chat_history[-8:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    messages = [
        {"role": "system", "content": QUIZ_GENERATOR_PROMPT},
        {"role": "user", "content": f"""大纲学习目标: {learning_goal}
当前选择资源/模块: {current_module_title if current_module_title else '无特定模块（基于大纲出题）'}

用户具体指令 (最重要，请务必遵循):
{user_message if user_message else "按照默认规则出题"}

对话历史（请结合上下文理解用户意图）:
{history_text if history_text else "无历史记录"}

学习内容摘要 (出题的绝对基础与核心范围):
{content_summary}

{pref_quiz_text}
{weak_text}

请根据以上信息生成练习题目，输出 JSON:"""}
    ]

    try:
        _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))
        
        def _emit_thinking_start(agent: str, prefix: str = ""):
            if _sse_cb:
                try:
                    _sse_cb(f'data: {json.dumps({"type": "thinking_start", "agent": agent, "content": prefix}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        def _emit_thinking_chunk(chunk: str):
            if _sse_cb:
                try:
                    _sse_cb(f'data: {json.dumps({"type": "thinking_chunk", "content": chunk}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        def _emit_thinking(content: str):
            if _sse_cb:
                try:
                    _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "题目生成智能体", "content": content}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        _emit_thinking("正在结合用户历史记录和薄弱知识点，构造练习题目...")

        _create_ph = state.get("create_placeholder_callback")
        placeholder_id = None
        if _create_ph:
            try:
                ph_map = _create_ph([{"module_type": "quiz", "title": f"测验: {quiz_target}"[:50], "description": "正在结合薄弱点生成测验..."}])
                if ph_map:
                    placeholder_id = list(ph_map.values())[0].get("id")
                    logger.info(f"  [题目生成智能体] 创建占位成功: {placeholder_id}")
            except Exception as e:
                logger.error(f"  [题目生成智能体] 创建占位失败: {e}")

        def on_chunk(chunk: str):
            if _sse_cb and placeholder_id:
                try:
                    _sse_cb(f'data: {json.dumps({"type": "resource_stream_text", "resource_id": placeholder_id, "content": chunk}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass

        logger.info(f"  [题目生成智能体] 正在调用 LLM...")
        result = llm.chat_json_stream(messages, max_tokens=4096, on_chunk=on_chunk)
        record_from_mimo(llm, state.get("user_id", 0), "quiz_generation", state.get("task_id"))
        questions = result.get("questions", [])
        custom_reqs = result.get("user_custom_requirements")

        has_custom = False
        if isinstance(custom_reqs, dict):
            has_custom = (
                bool(custom_reqs.get("types"))
                or custom_reqs.get("count") is not None
                or custom_reqs.get("difficulty") is not None
            )

        logger.info(f"  [题目生成智能体] 题目生成完成!")
        logger.info(f"    测验标题: {result.get('quiz_title', '未命名')}")
        logger.info(f"    题目数量: {len(questions)}")
        for i, q in enumerate(questions):
            qtype = q.get("question_type", "unknown")
            qtext = q.get("question_text", "")[:50]
            diff = q.get("difficulty", 3)
            logger.info(f"      题目{i+1} [{qtype}] 难度{diff}: {qtext}...")
        dist = result.get("difficulty_distribution", {})
        logger.info(f"    难度分布: 简单={dist.get('easy', 0)}, 中等={dist.get('medium', 0)}, 困难={dist.get('hard', 0)}")
        logger.info(f"{'='*60}")

        return_data = {
            "quiz_questions": questions,
            "quiz_config": {
                "title": result.get("quiz_title", ""),
                "description": result.get("description", ""),
                "total": result.get("total_questions", len(questions)),
            },
            "current_step": f"题目生成智能体: 已生成 {len(questions)} 道题目",
            "stream_events": [{
                "event_type": "quiz",
                "agent": "quiz_generator",
                "data": result,
                "step_description": f"已生成 {len(questions)} 道练习题"
            }],
        }
        if has_custom:
            return_data["_detected_quiz_requirements"] = custom_reqs
            logger.info(f"  [题目生成智能体] 检测到用户专门出题要求，标记转画像更新: {custom_reqs}")

        return return_data

    except Exception as e:
        logger.error(f"  [题目生成智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"题目生成失败: {str(e)}",
            "current_step": f"题目生成智能体: 生成失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "quiz_generator",
                "data": {"error": str(e)},
                "step_description": "题目生成失败"
            }],
        }
