"""
多模态资源自主生成智能体 - 当 RAG 中不存在相关资料时，直接调用大模型生成相关内容
后续实现 MCP 网络检索、多模态生成工具等
"""
import logging
from typing import Dict, Any
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_generator_llm

logger = logging.getLogger("agents.resource_generator")

SYSTEM_PROMPT = """你是一个专业的知识内容生成专家。当知识库中没有找到相关资料时，你需要根据自己的知识直接生成高质量的学习内容。

## 生成要求
1. 内容准确、专业、完整
2. 结构清晰，使用标题、列表、代码块等格式
3. 适当使用类比和举例帮助理解
4. 难度要匹配用户的知识基础
5. 如果涉及代码，要给出完整可运行的示例

## 输出格式
严格输出 JSON：
{
  "title": "内容标题",
  "content": "完整的 Markdown 格式内容",
  "key_points": ["要点1", "要点2"],
  "references": ["参考来源描述1"],
  "content_type": "text/code/mixed",
  "difficulty": "入门/初级/中级/高级"
}

## 规则
- 严禁使用 emoji 表情符号
- 所有文本使用中文
- 内容要充实，不要过于简略
- 代码示例要标注语言类型"""


def resource_generator_node(state: AgentState) -> Dict[str, Any]:
    """多模态资源自主生成智能体节点"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    task_breakdown = state.get("task_breakdown", {})
    user_profile = state.get("user_profile", {})
    rag_chunks = state.get("rag_context_chunks", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [资源生成智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")

    llm = get_resource_generator_llm()

    modules = task_breakdown.get("modules", [])
    if modules:
        covered_titles = set()
        for chunk in rag_chunks:
            for h in chunk.get("heading", []):
                covered_titles.add(h.lower())

        uncovered = []
        for m in modules:
            title = m.get("title", "")
            if not any(title.lower() in ct for ct in covered_titles):
                uncovered.append(m)

        if uncovered:
            target_module = uncovered[0]
            topic = f"{target_module.get('title', '')}: {target_module.get('description', '')}"
            logger.info(f"  [资源生成智能体] 发现 {len(uncovered)} 个未覆盖模块，生成: {target_module.get('title', '')}")
        else:
            topic = learning_goal
            logger.info(f"  [资源生成智能体] 所有模块已覆盖，生成通用内容")
    else:
        topic = learning_goal
        logger.info(f"  [资源生成智能体] 无模块信息，直接生成")

    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    style_hints = []
    if fs.get("visual_verbal", 0) < -0.3:
        style_hints.append("多使用图表、流程图描述")
    if fs.get("sensing_intuitive", 0) < -0.3:
        style_hints.append("多给出具体实例和实际案例")
    if fs.get("sequential_global", 0) < -0.3:
        style_hints.append("按照步骤顺序逐步讲解")

    style_text = "用户偏好: " + "; ".join(style_hints) if style_hints else ""
    if style_hints:
        logger.info(f"  [资源生成智能体] 风格偏好: {style_text}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""请生成以下主题的学习内容:

主题: {topic}
学习目标: {learning_goal}
{style_text}

请生成详细的学习内容，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [资源生成智能体] 正在调用 LLM 生成内容...")
        result = llm.chat_json(messages, max_tokens=8192)

        logger.info(f"  [资源生成智能体] 生成完成!")
        logger.info(f"    标题: {result.get('title', '未命名')}")
        logger.info(f"    类型: {result.get('content_type', '未知')}")
        logger.info(f"    难度: {result.get('difficulty', '未知')}")
        logger.info(f"    要点: {', '.join(result.get('key_points', []))}")
        logger.info(f"    内容长度: {len(result.get('content', ''))} 字符")
        logger.info(f"{'='*60}")

        return {
            "generated_content": result,
            "current_step": f"资源生成智能体: 已自主生成内容 [{result.get('title', '未命名')}]",
            "stream_events": [{
                "event_type": "content",
                "agent": "resource_generator",
                "data": result,
                "step_description": f"知识库无相关资料，已自主生成: {result.get('title', '')}"
            }],
        }

    except Exception as e:
        logger.error(f"  [资源生成智能体] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"资源自主生成失败: {str(e)}",
            "current_step": f"资源生成智能体: 生成失败 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "resource_generator",
                "data": {"error": str(e)},
                "step_description": "自主生成失败"
            }],
        }
