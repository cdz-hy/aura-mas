"""
多模态类型资源生成智能体 - 为指定类型（思维导图/总结/代码等）生成对应格式的学习资源
类似 quiz_generator 的直接生成流程，跳过 RAG 检索和内容编排
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_type_generator_llm

logger = logging.getLogger("agents.resource_type_generator")

# ==================== 各类型的系统提示 ====================

SYSTEM_PROMPTS = {
    "mindmap": """你是一个专业的思维导图生成专家。根据学习内容，生成结构清晰、层次分明的思维导图数据。

## 输出格式
严格输出 JSON，不要输出其他内容：
{
  "title": "思维导图标题",
  "description": "简要描述（单行文本）",
  "nodeData": {
    "id": "root",
    "topic": "中心主题",
    "expanded": true,
    "children": [
      {
        "id": "n1",
        "topic": "分支主题1",
        "children": [
          { "id": "n1_1", "topic": "子主题1.1" },
          { "id": "n1_2", "topic": "子主题1.2" }
        ]
      },
      {
        "id": "n2",
        "topic": "分支主题2",
        "children": [
          { "id": "n2_1", "topic": "子主题2.1" }
        ]
      }
    ]
  }
}

## 要求
- id 必须是唯一字符串（使用 "root", "n1", "n2", "n1_1" 等简单命名）
- topic 为节点显示文本，简洁明了，每个节点不超过 15 个字
- children 为子节点数组，层级不超过 4 层
- 一级分支 3-7 个，每个分支下 2-5 个子节点
- 内容要丰富完整，覆盖该主题的核心知识点
- 严禁使用 emoji 表情符号
- 可以适当基于当前内容扩展
- 所有文本使用中文""",

    "summary": """你是一个专业的知识总结专家。根据学习内容，生成精炼的总结回顾材料，适合快速复习。

## 输出格式
严格输出 JSON，不要输出其他内容：
{
  "title": "总结标题",
  "description": "简要描述（单行文本）",
  "content": "Markdown 格式的总结内容"
}

## 内容要求
- 提炼核心要点，去除冗余信息
- 使用标题、列表、加粗等格式突出重点
- 适当使用类比帮助记忆
- 最后附上"关键要点回顾"列表
- 严禁使用 emoji 表情符号
- 所有文本使用中文""",

    "code": """你是一个专业的编程教学专家。根据学习内容，生成高质量的代码示例和说明。

## 输出格式
严格输出 JSON，不要输出其他内容：
{
  "title": "代码示例标题",
  "description": "简要描述（单行文本）",
  "content": "Markdown 格式的代码内容"
}

## 内容要求
- 代码块必须标注语言类型（如 ```python）
- 代码要完整可运行，含必要的注释
- 先简要说明原理，再给出代码示例
- 代码后附上运行结果说明和注意事项
- 涉及多个知识点时，分别给出示例
- 严禁使用 emoji 表情符号
- 所有文本使用中文""",
}

# 通用的默认提示
SYSTEM_PROMPT_DEFAULT = """你是一个专业的学习内容生成专家。根据学习内容，生成指定类型的学习资源。

## 输出格式
严格输出 JSON，不要输出其他内容：
{
  "title": "资源标题",
  "description": "简要描述（单行文本）",
  "content": "Markdown 格式的内容"
}

## 要求
- 内容准确、专业、完整
- 结构清晰，使用标题、列表等格式
- 严禁使用 emoji 表情符号
- 所有文本使用中文"""


def resource_type_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    多模态类型资源生成智能体节点

    根据 state 中的资源类型，调用 LLM 生成对应格式的内容。
    类似 quiz_generator 的直接生成模式，不经过 RAG 和编排。
    """
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    task_breakdown = state.get("task_breakdown", {})
    user_profile = state.get("user_profile", {})
    rag_chunks = state.get("rag_context_chunks", [])
    chat_history = state.get("chat_history", [])
    source_resource_content = state.get("source_resource_content", "")

    # 从 task_breakdown 中提取目标资源类型
    modules = task_breakdown.get("modules", [])
    resource_type = "text"
    module_title = ""
    module_desc = ""
    if modules:
        module = modules[0]
        module_title = module.get("title", "")
        module_desc = module.get("description", "")
        resources = module.get("resources", [])
        if resources:
            resource_type = resources[0].get("resource_type", "text")

    logger.info(f"{'='*60}")
    logger.info(f"  [类型资源生成] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    logger.info(f"  目标类型: {resource_type}")
    logger.info(f"  模块标题: {module_title}")

    llm = get_resource_type_generator_llm()

    # 选择对应的系统提示
    system_prompt = SYSTEM_PROMPTS.get(resource_type, SYSTEM_PROMPT_DEFAULT)

    # 构造学习内容摘要（优先用源资源全文，否则用 RAG）
    content_summary = ""
    if source_resource_content:
        content_summary = source_resource_content
        logger.info(f"  [类型资源生成] 使用源资源全文作为上下文 ({len(source_resource_content)} 字符)")
    elif rag_chunks:
        parts = []
        for i, chunk in enumerate(rag_chunks[:10]):
            heading = " > ".join(chunk.get("heading", []))
            doc_title = chunk.get("doc_title", "")
            content = chunk.get("content", "")[:300]
            parts.append(f"[资料{i+1}] 来源: {doc_title}\n章节: {heading}\n内容: {content}")
        content_summary = "\n\n---\n\n".join(parts)
        logger.info(f"  [类型资源生成] 使用 RAG 检索结果作为上下文 ({len(rag_chunks)} 块)")

    # 用户偏好
    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    vv = fs.get("visual_verbal", 0)
    pref_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")

    # 对话历史
    history_text = ""
    if chat_history:
        recent = chat_history[-4:]
        lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role}: {msg['content'][:150]}")
        history_text = "\n".join(lines)

    # 构造用户消息
    user_content = f"""学习目标: {learning_goal}

对话历史:
{history_text if history_text else "无历史记录"}

当前模块信息:
- 标题: {module_title}
- 描述: {module_desc}
- 资源类型: {resource_type}

用户内容偏好: {pref_text}
"""

    if source_resource_content:
        user_content += f"\n## 源资源全文（请基于此内容生成）:\n{content_summary}\n"
    elif content_summary:
        user_content += f"\n## 检索到的相关知识资料:\n{content_summary}\n"
    else:
        user_content += "\n暂无检索到的知识资料，请基于学习目标自主生成。\n"

    user_content += f"\n请为该模块生成 {resource_type} 类型的学习资源，输出 JSON:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        logger.info(f"  [类型资源生成] 正在调用 LLM 生成 {resource_type}...")
        result = llm.chat_json(messages, max_tokens=8192)

        # 标准化输出
        generated = {
            "module_type": resource_type,
            "title": result.get("title", module_title),
            "description": result.get("description", module_desc),
            "content": "",
        }

        # mindmap 类型：content 字段是 nodeData 的 JSON 字符串
        if resource_type == "mindmap":
            node_data = result.get("nodeData")
            if node_data:
                import json
                generated["content"] = json.dumps(node_data, ensure_ascii=False)
            else:
                # 兼容 content 直接是 nodeData 的情况
                generated["content"] = result.get("content", "")
        else:
            generated["content"] = result.get("content", "")

        # 保留 metadata（如果有）
        if result.get("metadata"):
            generated["metadata"] = result["metadata"]

        logger.info(f"  [类型资源生成] 生成完成!")
        logger.info(f"    标题: {generated['title']}")
        logger.info(f"    类型: {resource_type}")
        logger.info(f"    内容长度: {len(generated['content'])} 字符")
        logger.info(f"{'='*60}")

        return {
            "generated_content": generated,
            "current_step": f"类型资源生成: 已生成 {resource_type} 类型资源「{generated['title']}」",
            "stream_events": [{
                "event_type": "resource_type_generated",
                "agent": "resource_type_generator",
                "data": generated,
                "step_description": f"已生成 {resource_type} 类型资源",
            }],
        }

    except Exception as e:
        logger.error(f"  [类型资源生成] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"{resource_type} 资源生成失败: {str(e)}",
            "current_step": f"类型资源生成: 生成失败 - {str(e)[:100]}",
            "stream_events": [{
                "event_type": "error",
                "agent": "resource_type_generator",
                "data": {"error": str(e)},
                "step_description": f"{resource_type} 资源生成失败",
            }],
        }
