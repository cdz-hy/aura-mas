"""
任务分解智能体 - 根据用户画像和学习目标生成个性化学习路径
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState, NODE_CONTROLLER, NODE_HUMAN_CONFIRM
from app.agents.llm_factory import get_task_decomposer_llm
from app.prompts import TASK_DECOMPOSER_PROMPT, TASK_DECOMPOSER_REACT_PROMPT
from app.agents.enhanced_search import (
    SearchHistoryTracker,
    execute_actions_parallel
)
from app.utils.token_recorder import record_from_mimo
from app.utils import stream_registry
import json

logger = logging.getLogger("agents.task_decomposer")


def task_decomposer_node(state: AgentState) -> Dict[str, Any]:
    """任务分解智能体节点"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    user_profile = state.get("user_profile", {})
    human_feedback = state.get("human_feedback", "")
    existing_plan = state.get("task_breakdown")

    logger.info(f"{'='*60}")
    logger.info(f"  [任务分解智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    if human_feedback:
        logger.info(f"  用户补充反馈: {human_feedback[:100]}")
    if existing_plan:
        logger.info(f"  已有学习路径: {existing_plan.get('title', '未命名')}")
    logger.info(f"  用户画像: {'有' if user_profile else '无'}")

    # 实时推送思考过程
    _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))
    
    def _emit_thinking(content: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "任务分解智能体", "content": content}, ensure_ascii=False)}\n\n')
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

    _emit_thinking("正在分析学习目标，规划个性化学习路径...")

    llm = get_task_decomposer_llm()

    profile_summary = _format_profile(user_profile)
    history_prefs = _extract_preferences(state.get("chat_history", []))

    # 构造对话历史上下文
    chat_history = state.get("chat_history", [])
    history_text = ""
    if chat_history:
        recent = chat_history[-8:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    logger.info(f"  [任务分解智能体] 画像摘要: {profile_summary[:200]}")

    # ==================== ReAct 自主搜索循环（最多2轮） ====================
    MAX_REACT_ROUNDS = 2
    history_tracker = SearchHistoryTracker()
    search_executed = False

    try:
        system_prompt = TASK_DECOMPOSER_REACT_PROMPT.format(max_rounds=MAX_REACT_ROUNDS)

        for round_num in range(1, MAX_REACT_ROUNDS + 1):
            logger.info(f"  [ReAct] 任务分解 - 第 {round_num} 轮思考")

            # 构建本轮 prompt
            if round_num == 1:
                user_prompt = f"""## 研究任务
学习主题/目标: {learning_goal}
用户画像及偏好:
{profile_summary}

这是第 1 轮，请判断是否需要使用网页搜索工具来验证/查询该主题的最新知识体系结构或核心大纲要点。
【重要原则】：如果你对此主题的知识结构非常清晰，无需搜索，请务必直接输出 decision 为 "finish"。"""
            else:
                history_summary = history_tracker.get_summary_for_llm(max_recent_snippets=10)
                user_prompt = f"""## 研究任务
学习主题/目标: {learning_goal}
用户画像及偏好:
{profile_summary}

{history_summary}

这是第 {round_num} 轮，请基于已有信息判断是否需要继续搜索，或选择 finish。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # 调用 LLM 进行 ReAct 决策
            _emit_thinking_start("任务分解智能体", "")
            react_result = llm.chat_json_stream(messages, on_chunk=_emit_thinking_chunk, stream_field="thought")
            logger.debug(f"  [ReAct] LLM 原始返回: {str(react_result)[:300]}")

            if not isinstance(react_result, dict):
                logger.warning(f"  [ReAct] LLM 返回非字典类型: {type(react_result)}，结束搜索")
                break

            thought = str(react_result.get("thought", ""))
            decision = str(react_result.get("decision", "finish")).lower().strip()
            actions = react_result.get("actions", [])

            if not isinstance(actions, list):
                actions = []

            logger.info(f"  [ReAct] 思考: {thought[:100]}...")
            logger.info(f"  [ReAct] 决策: {decision}, 动作数: {len(actions)}")

            if decision == "finish" or not actions:
                logger.info(f"  [ReAct] 结束自主搜索规划")
                _emit_thinking("决策完成: 结束自主搜索，开始生成学习路径大纲")
                break

            # 验证动作格式
            valid_actions = []
            for action in actions:
                if isinstance(action, dict):
                    action_type = action.get("action", "")
                    if action_type in ["search", "extract"]:
                        valid_actions.append(action)
                        if action_type == "search":
                            _emit_thinking(f"调用工具: 网页搜索 (关键词: {action.get('query', '')})")
                        elif action_type == "extract":
                            _emit_thinking(f"调用工具: 提取网页 (URL: {action.get('url', '')})")

            if not valid_actions:
                break

            search_executed = True
            # 并发执行所有有效动作
            action_results = execute_actions_parallel(valid_actions)

            # 更新历史记录
            for result in action_results:
                action_type = result.get("action_type", "")
                if action_type == "search":
                    query = result.get("query", "")
                    results = result.get("results", [])
                    images = result.get("images", [])
                    if results or images:
                        history_tracker.add_search_result(query, results, images)
                    _emit_thinking(f"网页搜索完成: 找到 {len(results)} 条相关结果，{len(images)} 张图片")
                elif action_type == "extract":
                    url = result.get("url", "")
                    title = result.get("title", "")
                    content = result.get("content", "")
                    success = result.get("success", False)
                    if success and content:
                        history_tracker.add_extracted_page(url, title, content)
                        _emit_thinking(f"提取网页完成: 成功读取页面「{title}」({len(content)} 字符)")
                    else:
                        _emit_thinking(f"提取网页失败: 无法读取该页面")

    except Exception as e:
        logger.warning(f"  [任务分解智能体] ReAct 搜索规划异常: {str(e)}，降级为直接生成")

    record_from_mimo(llm, state.get("user_id", 0), "task_decomposition_react", state.get("task_id"))

    # 构建最终生成的参考搜索内容
    search_context = ""
    if search_executed:
        all_content = history_tracker.get_all_content_for_generation()
        snippets = all_content["snippets"]
        extracted_pages = all_content["extracted_pages"]

        snippet_lines = []
        for i, snippet in enumerate(snippets[:15], 1):
            title = snippet.get("title", "无标题")
            text = (snippet.get("snippet", "") or "")[:300]
            snippet_lines.append(f"[{i}] {title}\n    {text}")

        page_lines = []
        for i, (url, content) in enumerate(list(extracted_pages.items())[:2], 1):
            page_lines.append(f"[网页参考{i}] {url}\n    {content[:1500]}...")

        search_context = "\n## 搜索到的参考网络资料\n"
        if snippet_lines:
            search_context += "### 网页片段\n" + "\n\n".join(snippet_lines) + "\n\n"
        if page_lines:
            search_context += "### 详细网页内容\n" + "\n\n".join(page_lines) + "\n\n"

    # 有已有计划 + 用户反馈 → 增量优化模式
    if existing_plan and human_feedback:
        import json as _json
        existing_plan_text = _json.dumps(existing_plan, ensure_ascii=False, indent=2)
        user_prompt = f"""已有学习路径需要根据用户反馈进行优化。

## 已有学习路径（请在此基础上优化，不要从零开始）
```json
{existing_plan_text}
```

## 用户补充/修改意见
{human_feedback}

## 学习目标
{learning_goal}

{search_context}

## 对话历史（请结合上下文理解用户意图）
{history_text if history_text else "无历史记录"}

## 用户画像
{profile_summary}

## 用户对话中表达的偏好
{history_prefs}

请根据用户意见在已有路径基础上优化，输出完整的学习路径 JSON："""
    else:
        # 全新生成模式
        user_prompt = f"""请根据以下信息生成学习路径分解：

## 学习目标
{learning_goal}

{search_context}

## 对话历史（请结合上下文理解用户意图）
{history_text if history_text else "无历史记录"}

## 用户画像
{profile_summary}

## 用户对话中表达的偏好
{history_prefs}

请输出 JSON 格式的学习路径分解："""

    messages = [
        {"role": "system", "content": TASK_DECOMPOSER_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        logger.info(f"  [任务分解智能体] 正在调用 LLM 生成学习路径...")
        _emit_thinking_start("任务分解智能体", "")
        result = llm.chat_json_stream(messages, on_chunk=_emit_thinking_chunk, stream_field="analysis")
        record_from_mimo(llm, state.get("user_id", 0), "task_decomposition", state.get("task_id"))

        modules = result.get("modules", [])
        needs_decomposition = result.get("needs_decomposition", len(modules) > 1)
        analysis = result.get("analysis", "")
        clarification_needed = result.get("clarification_needed")

        if clarification_needed:
            logger.warning(f"  [任务分解智能体] 目标不明确/存在歧义，请求追问: {clarification_needed}")
            # chunk 事件 → 前端流式显示（onChunk → streamBuffer）
            _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))
            if _sse_cb:
                try:
                    _sse_cb(f'data: {json.dumps({"type": "chunk", "content": clarification_needed}, ensure_ascii=False)}\n\n')
                except Exception:
                    pass
            return {
                "_pending_question": clarification_needed,
                "needs_human_confirm": True,
                "current_step": f"任务分解智能体: 目标不明确，等待用户澄清",
                "stream_events": [
                    # content 事件 → graph_event_to_sse → node_content → 后端入库（_save_plain_text_reply）
                    {"event_type": "content", "agent": "task_decomposer", "data": {"text": clarification_needed}},
                    {"event_type": "thinking", "agent": "task_decomposer", "data": {"message": f"目标存在歧义，需要澄清: {clarification_needed}"}, "step_description": "目标存在歧义，请求澄清"},
                ],
            }

        logger.info(f"  [任务分解智能体] 学习路径生成成功!")
        logger.info(f"    需分解: {'是' if needs_decomposition else '否 (单模块直接生成)'}")
        if analysis:
            logger.info(f"    分析: {analysis[:120]}")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    难度: {result.get('difficulty_level', '未知')}")
        logger.info(f"    预估时长: {result.get('estimated_duration', '未知')}")
        logger.info(f"    模块数量: {len(modules)}")
        for i, m in enumerate(modules):
            logger.info(f"      模块{i+1}: {m.get('title', '')} - {m.get('description', '')[:50]}")

        # 自主异常检测：检查分解内容是否与原始目标偏离
        anomaly_summary = f"标题: {result.get('title', '')}; 模块: " + "; ".join(
            f"{m.get('title', '')}: {m.get('description', '')}" for m in modules[:3]
        )
        from app.agents.anomaly_checker import check_content_alignment
        is_aligned, anomaly_reason = check_content_alignment(learning_goal, anomaly_summary, state.get("user_id", 0), state.get("task_id"))
        if not is_aligned:
            logger.warning(f"  [任务分解智能体] 自主检测到内容偏离: {anomaly_reason}")
            logger.warning(f"  [任务分解智能体] 中断当前流程 -> 回到主控")
            return {
                "agent_anomaly": True,
                "anomaly_reason": anomaly_reason,
                "current_step": f"任务分解智能体: 检测到内容偏离 - {anomaly_reason}",
                "stream_events": [{
                    "event_type": "thinking",
                    "agent": "task_decomposer",
                    "data": {"message": f"检测到分解内容与原始目标偏离: {anomaly_reason}"},
                    "step_description": f"异常中断: {anomaly_reason}"
                }],
            }

        logger.info(f"{'='*60}")

        if needs_decomposition:
            # 多模块 → 需要用户确认
            logger.info(f"  [任务分解智能体] 进入用户确认流程")
            return {
                "task_breakdown": result,
                "learning_goal": learning_goal,
                "task_breakdown_confirmed": False,
                "human_feedback": None,
                "needs_human_confirm": True,
                "current_step": f"任务分解智能体: 已生成学习路径 [{result.get('title', '未命名')}]，包含 {len(modules)} 个模块，等待确认",
                "stream_events": [
                    {
                        "event_type": "task_breakdown",
                        "agent": "task_decomposer",
                        "data": result,
                        "step_description": f"学习路径规划完成 ({len(modules)} 个模块)，请确认或补充说明"
                    },
                    {
                        "event_type": "confirm_needed",
                        "agent": "task_decomposer",
                        "data": {
                            "message": f"分析: {analysis}\n\n学习路径已生成，请确认或继续补充",
                            "task_breakdown": result,
                        },
                        "step_description": "请确认学习路径"
                    },
                ],
            }
        else:
            # 单模块 → 自动确认，跳过人工确认直接进入 RAG 检索
            logger.info(f"  [任务分解智能体] 单模块主题，自动确认，跳过人工确认 -> RAG检索")
            return {
                "task_breakdown": result,
                "learning_goal": learning_goal,
                "task_breakdown_confirmed": True,
                "human_feedback": None,
                "needs_human_confirm": False,
                "current_step": f"任务分解智能体: 识别为单模块主题 [{result.get('title', '未命名')}]，直接进入检索",
                "stream_events": [
                    {
                        "event_type": "task_breakdown",
                        "agent": "task_decomposer",
                        "data": result,
                        "step_description": f"识别为聚焦主题: {analysis}"
                    },
                ],
            }
    except Exception as e:
        logger.error(f"  [任务分解智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"任务分解失败: {str(e)}",
            "current_step": f"任务分解智能体: 生成失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "task_decomposer",
                "data": {"error": str(e)},
                "step_description": "任务分解失败"
            }],
        }


def _format_profile(profile: Dict[str, Any]) -> str:
    """格式化用户画像为文本摘要"""
    if not profile:
        return "暂无用户画像信息"

    parts = []
    if profile.get("domain"):
        parts.append(f"领域: {profile['domain']}")
    if profile.get("age"):
        parts.append(f"年龄: {profile['age']}")
    if profile.get("gender"):
        parts.append(f"性别: {profile['gender']}")

    behavior = profile.get("learning_behavior", {})
    # 确保画像字典结构完整，双向对齐嵌套与扁平两套命名规范
    from app.utils.profile_utils import ensure_learning_behavior_fields
    behavior = ensure_learning_behavior_fields(behavior)

    if behavior:
        goal_orientation = behavior.get("goal_orientation", "exam")
        goal_map = {
            "career": "职业发展 (career)",
            "exam": "考试提分 (exam)",
            "interest": "兴趣学习 (interest)",
            "research": "学术研究 (research)",
            "skill": "技能提升 (skill)"
        }
        goal_zh = goal_map.get(goal_orientation, goal_orientation)
        parts.append(f"目标导向: {goal_zh}")

        knowledge = behavior.get("knowledge_base", [])
        if knowledge:
            parts.append(f"已有知识基础: {', '.join(knowledge)}")

        weak_areas = behavior.get("weak_areas", [])
        if weak_areas:
            parts.append(f"薄弱环节: {', '.join(weak_areas)}")

        interest_tags = behavior.get("interest_tags", [])
        if interest_tags:
            parts.append(f"兴趣标签: {', '.join(interest_tags)}")

        # 使用标准的扁平字段名称进行安全获取，支持精确浮点值显示
        si = behavior.get("sensing_vs_intuitive", 0.0)
        vv = behavior.get("visual_vs_verbal", 0.0)
        ar = behavior.get("active_vs_reflective", 0.0)
        sg = behavior.get("sequential_vs_global", 0.0)

        dimensions = [
            f"{'感官型(Sensing)' if si < 0 else '直觉型(Intuitive)'}(数值: {si:.2f})",
            f"{'视觉型(Visual)' if vv < 0 else '言语型(Verbal)'}(数值: {vv:.2f})",
            f"{'活跃型(Active)' if ar < 0 else '沉思型(Reflective)'}(数值: {ar:.2f})",
            f"{'序列型(Sequential)' if sg < 0 else '全局型(Global)'}(数值: {sg:.2f})"
        ]
        parts.append(f"学习风格偏好及倾向数值(范围[-1,1]): {'; '.join(dimensions)}")

        pref_quiz = behavior.get("preferred_quiz_types", [])
        if pref_quiz:
            parts.append(f"偏好题型: {', '.join(pref_quiz)}")

        pref_resources = behavior.get("preferred_resource_types", [])
        if pref_resources:
            parts.append(f"偏好资源: {', '.join(pref_resources)}")

    return "\n".join(parts) if parts else "暂无详细画像信息"


def _extract_preferences(chat_history: List[Dict[str, str]]) -> str:
    """从对话历史中提取用户偏好"""
    if not chat_history:
        return "暂无对话记录"

    recent_user = [m["content"] for m in chat_history if m["role"] == "user"][-5:]
    if not recent_user:
        return "暂无用户发言"

    return "用户近期发言:\n" + "\n".join(f"- {m}" for m in recent_user)
