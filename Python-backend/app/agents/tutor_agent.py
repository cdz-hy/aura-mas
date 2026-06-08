"""
智能辅导智能体 - 针对用户当前点击的模块内容进行个性化辅导
独立端点调用，不加入主 LangGraph 图
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.agents.llm_factory import get_tutor_llm
from app.agents.search_utils import search_tavily, execute_searches, format_search_results
from app.services.db.java_client import java_client
from app.services.retrieval import HybridRetrievalService
from app.agents.conversation_compressor import build_chat_history_with_context
from app.utils.profile_utils import ensure_learning_behavior_fields, update_learning_behavior

logger = logging.getLogger("agents.tutor_agent")

RETRIEVAL_SERVICE: HybridRetrievalService = None


def _get_retrieval_service() -> HybridRetrievalService:
    global RETRIEVAL_SERVICE
    if RETRIEVAL_SERVICE is None:
        RETRIEVAL_SERVICE = HybridRetrievalService()
    return RETRIEVAL_SERVICE


ANALYSIS_PROMPT = """你是一个智能辅导助手。用户正在学习某个模块，针对该模块提出了问题。

## 你的任务
1. 判断用户的问题是否与当前模块内容相关
2. 如果相关，提取 2-3 个搜索关键点，用于检索更详细的解答资料
3. 如果不相关，礼貌地引导用户回到当前模块主题

## 搜索关键点规则（极其重要）
- 每个关键点必须是**自包含的完整查询**，单独拿出来就能准确表达用户意图
- **严禁拆分**：不要把「南昌航空大学软件学院」拆成「南昌航空大学」和「软件学院」，应保持为「南昌航空大学软件学院」
- 保留所有修饰语和限定词，确保上下文不丢失
- 每个关键点应是一个有意义的、独立的搜索查询短语

## 输出格式
严格输出 JSON：
{
  "related": true/false,
  "search_points": ["完整查询1", "完整查询2"],
  "analysis": "简要分析用户问题与模块内容的关系"
}"""


NO_RESOURCE_ANALYSIS_PROMPT = """你是一个智能辅导助手。用户没有选择具体的学习模块，直接向你提问。

## 你的任务
1. 判断用户的问题是否明确，能否判断出用户想要学习或了解什么
2. 如果问题明确（比如问了具体的知识点、概念、技术问题等），提取 2-3 个搜索关键点
3. 如果问题不明确（比如只说了"帮帮我"、"我想学习"但没说学什么，或表述含糊不清），生成一句礼貌的追问，结合用户刚刚说的话引导用户说清楚想学什么

## 搜索关键点规则（极其重要）
- 每个关键点必须是**自包含的完整查询**，单独拿出来就能准确表达用户意图
- **严禁拆分**：例如：不要把「南昌航空大学软件学院」拆成「南昌航空大学」和「软件学院」，应保持为「南昌航空大学软件学院」
- 保留所有修饰语和限定词，确保上下文不丢失
- 每个关键点应是一个有意义的、独立的搜索查询短语

## 输出格式
严格输出 JSON：
{
  "clear": true/false,
  "search_points": ["完整查询1", "完整查询2"],
  "clarification": "如果问题不明确，这里是礼貌的追问内容；如果问题明确则为空字符串"
}"""

RESPONSE_PROMPT = """你是一个友好的智能辅导助手。用户正在学习某个模块，针对该模块提出了问题。

## 回答规则
1. 紧密结合当前模块内容回答问题
2. 如果有检索到的资料，优先使用资料中的信息
3. 回答要分点清晰，便于理解
4. 在回答末尾给出 1-2 条学习建议
5. 严禁使用 emoji 表情符号
6. 使用中文回复
7. 回答简洁明了，避免冗长，控制在 500 字以内
8. 如果提供了「可用的相关图片」，在回答中引用最相关的图片（最多2张），使用 Markdown 图片语法 ![描述](URL)。只引用与回答内容密切相关的图片，如果图片与问题无关则不引用。图片引用应自然融入回答内容中"""


TUTOR_PROFILE_PROMPT = """你是一个用户画像分析助手。根据辅导对话内容，分析用户的学习特征变化。

## 分析维度
- 学习风格维度（增量值，范围 -0.3 ~ +0.3）：
  - visual_vs_verbal: 视觉型(-1) ↔ 言语型(+1)
  - active_vs_reflective: 活跃型(-1) ↔ 沉思型(+1)
  - sensing_vs_intuitive: 感官型(-1) ↔ 直觉型(+1)
  - sequential_vs_global: 序列型(-1) ↔ 全局型(+1)
- 知识相关（列表字段，输出期望的最终状态）：
  - knowledge_base: 已掌握的知识
  - weak_areas: 薄弱点
  - interest_tags: 兴趣标签
- 其他：
  - preferred_resource_types: 偏好的资源类型
  - goal_orientation: career/exam/interest/skill

## 输出格式
严格输出 JSON：
{
  "should_update": true/false,
  "confidence": 0.0-1.0,
  "updates": {
    "visual_vs_verbal": 增量值或null,
    "active_vs_reflective": 增量值或null,
    "sensing_vs_intuitive": 增量值或null,
    "sequential_vs_global": 增量值或null,
    "knowledge_base": [...完整列表...] 或 null,
    "weak_areas": [...完整列表...] 或 null,
    "interest_tags": [...完整列表...] 或 null,
    "preferred_resource_types": [...] 或 null,
    "goal_orientation": "..." 或 null
  },
  "analysis": "简要分析依据"
}

## 注意
- 学习风格维度只输出增量（如 +0.1 或 -0.1），不要输出绝对值
- 列表字段输出期望的最终完整列表，不是增量
- 如果没有足够信息判断，should_update 设为 false"""


def _format_module_content(resource: Dict[str, Any]) -> str:
    """格式化模块内容为 LLM 可读文本"""
    module_type = resource.get("moduleType", "text")
    md = resource.get("moduleData", {})
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except Exception:
            md = {}

    title = md.get("title", resource.get("title", "未知模块"))
    content = md.get("content", "")
    description = md.get("description", "")

    parts = [f"模块类型: {module_type}", f"标题: {title}"]
    if description:
        parts.append(f"描述: {description}")
    if content:
        # 截断过长内容
        if len(content) > 3000:
            content = content[:3000] + "...(内容已截断)"
        parts.append(f"内容:\n{content}")
    return "\n".join(parts)


def _format_quiz_records(records: List[Dict]) -> str:
    """格式化用户作答记录"""
    if not records:
        return "暂无作答记录"
    lines = []
    for i, r in enumerate(records[:10], 1):
        question = r.get("questionText", r.get("question", ""))
        user_answer = r.get("userAnswer", "")
        is_correct = r.get("isCorrect", 0)
        correct_answer = r.get("correctAnswer", "")
        status = "正确" if is_correct else "错误"
        lines.append(f"第{i}题: {question[:100]}")
        lines.append(f"  用户答案: {user_answer} ({status})")
        if not is_correct:
            lines.append(f"  正确答案: {correct_answer}")
    return "\n".join(lines)


def _emit(sse_callback, event_type: str, content: str):
    """推送 SSE 事件"""
    if sse_callback:
        try:
            sse_callback(f'data: {json.dumps({"type": event_type, "content": content}, ensure_ascii=False)}\n\n')
        except Exception:
            pass


async def tutor_chat(
    user_id: int,
    plan_id: int,
    session_id: str,
    resource_id: int,
    user_message: str,
    sse_callback=None,
) -> str:
    """
    智能辅导核心流程。
    resource_id=0 时为无资源模式，直接围绕用户问题回答。

    Returns:
        AI 回复文本
    """
    llm = get_tutor_llm()
    has_resource = resource_id > 0

    # 1. 获取模块内容（仅在有资源时）
    module_content = ""
    module_type = "text"
    quiz_text = ""
    if has_resource:
        _emit(sse_callback, "progress", "正在获取模块内容...")
        resource = {}
        try:
            resource = java_client.get_resource_by_id(resource_id)
        except Exception as e:
            logger.warning(f"  [辅导智能体] 获取资源失败: {e}")

        if resource:
            module_content = _format_module_content(resource)
            module_type = resource.get("moduleType", "text")

        # 2. 如果是 quiz 类型，获取作答记录
        if module_type == "quiz":
            try:
                records = java_client.get_quiz_records_by_resource(user_id, resource_id)
                quiz_text = _format_quiz_records(records)
            except Exception as e:
                logger.warning(f"  [辅导智能体] 获取作答记录失败: {e}")

    # 3. 获取对话历史（带压缩上下文）
    chat_history = []
    try:
        raw_history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id, session_id=session_id, limit=200
        )
        chat_history = build_chat_history_with_context(raw_history)
    except Exception:
        pass

    # 构建历史文本
    history_text = ""
    recent = chat_history[-20:]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        history_text += f"{role}: {msg['content'][:200]}\n"

    # 4. 简单问题检测（问候、身份、感谢等，无需 RAG/搜索）
    import re
    _simple_pattern = re.compile(
        r'^(你好|嗨|哈喽|hi|hello|hey|你是谁|你叫什么|你能做什么|'
        r'谢谢|感谢|thanks|thank|好的|明白了|知道了|嗯|哦|'
        r'再见|拜拜|bye|早上好|下午好|晚上好|早安|晚安|'
        r'帮帮我|帮忙|在吗|在不在|有人吗)'
        r'[\s!?！？。.~]*$', re.IGNORECASE
    )
    is_simple = bool(_simple_pattern.match(user_message.strip()))

    # 5. 分析 + 提取搜索关键点
    search_points = [user_message]
    related = True
    analysis_text = ""

    # 5a. 无资源模式：LLM 判断用户意图是否明确
    no_resource_clarification = ""
    if not has_resource and not is_simple:
        _emit(sse_callback, "progress", "正在理解你的问题...")
        no_resource_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-800:]}" if history_text else ""}

请判断用户的问题是否明确，输出 JSON:"""

        no_resource_messages = [
            {"role": "system", "content": NO_RESOURCE_ANALYSIS_PROMPT},
            {"role": "user", "content": no_resource_input},
        ]

        try:
            nr_analysis = llm.chat_json(no_resource_messages, max_tokens=512)
            is_clear = nr_analysis.get("clear", True)
            if is_clear:
                sp = nr_analysis.get("search_points", [])
                search_points = sp if sp else [user_message]
                logger.info(f"  [辅导智能体] 无资源-意图明确, 搜索点: {search_points}")
            else:
                no_resource_clarification = nr_analysis.get("clarification", "")
                logger.info(f"  [辅导智能体] 无资源-意图不明确, 追问: {no_resource_clarification[:80]}")
        except Exception as e:
            logger.warning(f"  [辅导智能体] 无资源意图分析失败: {e}")

    if has_resource:
        _emit(sse_callback, "progress", "正在分析问题...")
        analysis_input = f"""## 当前模块内容
{module_content}

{f"## 用户作答记录{chr(10)}{quiz_text}" if quiz_text else ""}

## 用户问题
{user_message}

## 对话历史
{history_text[-1000:] if history_text else "无"}

请分析用户问题与模块内容的相关性，输出 JSON:"""

        analysis_messages = [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": analysis_input},
        ]

        try:
            analysis = llm.chat_json(analysis_messages, max_tokens=512)
            related = analysis.get("related", True)
            search_points = analysis.get("search_points", [user_message])
            analysis_text = analysis.get("analysis", "")
        except Exception:
            pass

        logger.info(f"  [辅导智能体] 相关性: {related}, 分析: {analysis_text[:80]}")

    # 5. RAG 检索（简单问题跳过，意图不明确时也跳过）
    rag_context = ""
    available_images: List[Dict[str, str]] = []
    logger.info(f"  [辅导智能体] RAG判断: is_simple={is_simple}, no_resource_clarification='{no_resource_clarification}', search_points={search_points}")
    if not is_simple and not no_resource_clarification:
        _emit(sse_callback, "progress", "正在检索知识库...")
        try:
            service = _get_retrieval_service()
            rag_tasks = []
            for point in search_points[:3]:
                rag_tasks.append(service.search(query=point, limit=10, rerank_top_n=5, min_rerank_score=0.5))
            rag_results = await asyncio.gather(*rag_tasks, return_exceptions=True)

            all_chunks = []
            for result in rag_results:
                if isinstance(result, dict):
                    for chunk in result.get("context_chunks", []):
                        content = chunk.get("content", "")
                        if content and len(content) > 50:
                            all_chunks.append(content[:500])
                        # 提取图片（最多 2 张）
                        if chunk.get("image_path") and len(available_images) < 2:
                            available_images.append({
                                "url": chunk["image_path"],
                                "caption": chunk.get("image_caption", ""),
                            })

            if all_chunks:
                rag_context = "\n\n".join(f"[资料{i+1}] {c}" for i, c in enumerate(all_chunks[:5]))
                logger.info(f"  [辅导智能体] RAG 检索到 {len(all_chunks)} 条资料, {len(available_images)} 张图片")
        except Exception as e:
            logger.warning(f"  [辅导智能体] RAG 检索失败: {e}")

    # 6. RAG 不足时，网络搜索（简单问题跳过，意图不明确时也跳过）
    web_context = ""
    logger.info(f"  [辅导智能体] 网络搜索判断: is_simple={is_simple}, rag_context为空={not rag_context}, no_resource_clarification='{no_resource_clarification}'")
    if not is_simple and not rag_context and not no_resource_clarification:
        _emit(sse_callback, "progress", "知识库未找到相关内容，正在网络搜索...")
        try:
            queries = search_points[:3]
            logger.info(f"  [辅导智能体] 网络搜索查询: {queries}")
            results, web_images = execute_searches(queries)
            if results:
                web_context = format_search_results(results[:10])
                logger.info(f"  [辅导智能体] 网络搜索到 {len(results)} 条结果")
            # RAG 没有图片时，从 web 搜索中取
            if not available_images and web_images:
                for img in web_images[:5]:
                    if img.get("url"):
                        available_images.append({
                            "url": img["url"],
                            "caption": img.get("description", ""),
                        })
                logger.info(f"  [辅导智能体] 网络搜索图片 {len(available_images)} 张")
        except Exception as e:
            logger.warning(f"  [辅导智能体] 网络搜索失败: {e}")

    # 7. 意图不明确时，直接返回追问（跳过 LLM 生成）
    if no_resource_clarification:
        _emit(sse_callback, "progress", "")
        _emit(sse_callback, "chunk", no_resource_clarification)
        _emit(sse_callback, "done", "")
        logger.info(f"  [辅导智能体] 返回追问: {no_resource_clarification[:80]}")
        return no_resource_clarification

    # 7. LLM 生成流式回答
    _emit(sse_callback, "progress", "正在生成回答...")

    context_section = ""
    if rag_context:
        context_section = f"\n\n## 检索到的知识资料\n{rag_context}"
    elif web_context:
        context_section = f"\n\n## 网络搜索结果\n{web_context}"

    # 构建图片上下文
    image_section = ""
    if available_images:
        img_lines = []
        for i, img in enumerate(available_images):
            desc = img["caption"] or "相关图片"
            img_lines.append(f"图片{i+1}: ![ {desc} ]({img['url']})")
        image_section = "\n\n## 可用的相关图片\n" + "\n".join(img_lines)

    # 根据是否有资源模块构建不同的 prompt
    if is_simple:
        response_input = f"""## 用户问题
{user_message}

请简洁友好地回复用户。如果是问候，简短回应并询问有什么学习上的问题可以帮忙。"""
    elif has_resource and related:
        response_input = f"""## 当前模块内容
{module_content}

{f"## 用户作答记录{chr(10)}{quiz_text}" if quiz_text else ""}

## 用户问题
{user_message}

## 问题分析
{analysis_text}
{context_section}
{image_section}

请结合模块内容和检索资料，回答用户的问题，并给出学习建议。"""
    else:
        # 无资源模式，或问题与模块不相关
        response_input = f"""## 用户问题
{user_message}

{f"## 对话历史{chr(10)}{history_text[-1000:]}" if history_text else ""}
{context_section}
{image_section}

请回答用户的问题。如果有检索资料，优先使用资料中的信息。回答分点清晰，末尾给出 1-2 条学习建议。"""

    response_messages = [
        {"role": "system", "content": RESPONSE_PROMPT},
        {"role": "user", "content": response_input},
    ]

    ai_response = ""
    # 追踪段落边界位置，用于图片插入
    para_breaks: List[int] = []
    try:
        for chunk in llm.chat_stream(response_messages, max_tokens=2048):
            ai_response += chunk
            _emit(sse_callback, "chunk", chunk)
    except Exception as e:
        logger.error(f"  [辅导智能体] 生成回答失败: {e}")
        ai_response = ai_response or "抱歉，生成回答时出现错误，请稍后再试。"
        if not ai_response:
            _emit(sse_callback, "chunk", ai_response)

    # 记录段落边界（\n\n 的位置）
    search_from = 0
    while True:
        idx = ai_response.find("\n\n", search_from)
        if idx == -1:
            break
        para_breaks.append(idx + 2)
        search_from = idx + 2

    # 如果 LLM 未引用图片，在第一个段落边界后插入
    if available_images and not any(img["url"] in ai_response for img in available_images):
        img_md_parts = []
        for img in available_images:
            desc = img["caption"] or "相关图片"
            img_md_parts.append(f"\n![{desc}]({img['url']})\n")
        img_block = "\n".join(img_md_parts)

        if para_breaks:
            insert_pos = para_breaks[0]
            corrected = ai_response[:insert_pos] + img_block + ai_response[insert_pos:]
        else:
            corrected = ai_response + img_block

        _emit(sse_callback, "replace", corrected)
        ai_response = corrected
        logger.info(f"  [辅导智能体] 图片已插入到第 1 个段落后")

    _emit(sse_callback, "done", "")
    logger.info(f"  [辅导智能体] 回答完成，长度: {len(ai_response)} 字符")

    # 8. 异步更新用户画像（合并式更新，不覆盖）
    try:
        user_profile = java_client.get_user_profile(user_id)
        current_behavior = ensure_learning_behavior_fields(user_profile.get("learning_behavior", {}))

        profile_input = f"""## 当前用户画像
- 知识基础: {current_behavior.get('knowledge_base', [])}
- 薄弱点: {current_behavior.get('weak_areas', [])}
- 兴趣标签: {current_behavior.get('interest_tags', [])}
- 视觉-言语: {current_behavior.get('visual_vs_verbal', 0.0)}
- 活跃-沉思: {current_behavior.get('active_vs_reflective', 0.0)}
- 感官-直觉: {current_behavior.get('sensing_vs_intuitive', 0.0)}
- 序列-全局: {current_behavior.get('sequential_vs_global', 0.0)}
- 偏好资源类型: {current_behavior.get('preferred_resource_types', [])}
- 目标导向: {current_behavior.get('goal_orientation', 'career')}

## 辅导对话
用户: {user_message}
助手: {ai_response[:500]}

请分析是否有需要更新的画像信息，输出 JSON:"""

        profile_messages = [
            {"role": "system", "content": TUTOR_PROFILE_PROMPT},
            {"role": "user", "content": profile_input},
        ]

        profile_result = llm.chat_json(profile_messages, max_tokens=1024)
        should_update = profile_result.get("should_update", False)
        updates = profile_result.get("updates", {})
        confidence = profile_result.get("confidence", 0.5)

        if should_update and updates:
            # 使用与 LangGraph 相同的合并逻辑
            updated_behavior = update_learning_behavior(
                current=current_behavior,
                updates=updates,
                confidence=confidence,
            )
            reason = profile_result.get("analysis", "辅导对话自动更新")
            java_client.save_user_profile(user_id, updated_behavior, reason)
            logger.info(f"  [辅导智能体] 画像更新成功 (置信度: {confidence:.2f})")
        else:
            logger.info(f"  [辅导智能体] 无需更新画像")
    except Exception as e:
        logger.warning(f"  [辅导智能体] 画像更新失败: {e}")

    return ai_response
