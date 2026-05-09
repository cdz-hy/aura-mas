"""
内容编排智能体 - 将 RAG 检索结果规划排版为模块化的顺序合理、排版美观的多模态学习资源
采用 mimo-v2.5 标准模型（唯一使用标准模型的智能体）
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_content_orchestrator_llm

logger = logging.getLogger("agents.content_orchestrator")

SYSTEM_PROMPT = """你是一个专业的内容编排专家。你的任务是将检索到的多模态知识内容，按照合理美观的顺序和模块化结构编排为学习资源。

## 编排要求
1. 按照逻辑顺序组织内容模块，由浅入深
2. 每个模块结构清晰，标题层次分明
3. 图片资源要附带说明注解，使用 Markdown 图片格式
4. 代码块要标注语言类型
5. 重要概念用加粗或引用格式标注
6. 模块间要有合理的过渡说明

## 输出格式
严格输出 JSON：
{
  "title": "学习资源总标题",
  "description": "简要描述",
  "modules": [
    {
      "module_order": 1,
      "module_type": "text",
      "title": "模块标题",
      "content": "模块内容（Markdown格式）",
      "metadata": {
        "key_concepts": ["概念1", "概念2"],
        "has_images": true,
        "has_code": false,
        "estimated_read_time": "5分钟"
      }
    }
  ],
  "total_modules": 5,
  "summary": "学习资源总结"
}

## module_type 取值
- text: 文本内容
- image: 图片说明
- diagram: 流程图/思维导图描述
- code: 代码示例
- quiz: 随堂测验
- summary: 总结回顾

## 规则
- 严禁使用 emoji 表情符号
- 所有文本使用中文
- 图片使用 Markdown 格式: ![描述](URL)
- 内容要完整充实，不要过于简略"""


def content_orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """内容编排智能体节点"""
    rag_chunks = state.get("rag_context_chunks", [])
    task_breakdown = state.get("task_breakdown", {})
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    user_profile = state.get("user_profile", {})
    generated_content = state.get("generated_content")

    logger.info(f"{'='*60}")
    logger.info(f"  [内容编排智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    logger.info(f"  输入内容块: {len(rag_chunks)} 个")
    logger.info(f"  自主生成内容: {'有' if generated_content else '无'}")

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
        modules_desc = "\n".join([
            f"- 模块{m.get('module_id', i+1)}: {m.get('title', '')} - {m.get('description', '')}"
            for i, m in enumerate(modules)
        ])

    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    vv = fs.get("visual_verbal", 0)
    pref_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")
    logger.info(f"  [内容编排智能体] 用户内容偏好: {pref_text}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

参考学习路径:
{modules_desc}

用户内容偏好: {pref_text}

检索到的知识资料:
{content_text}
{generated_text}

请将以上资料编排为结构化的学习资源，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [内容编排智能体] 正在调用 LLM 进行内容编排...")
        result = llm.chat_json(messages, max_tokens=8192)
        modules_list = result.get("modules", [])

        logger.info(f"  [内容编排智能体] 编排完成!")
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
            "current_step": f"内容编排智能体: 完成编排，共 {len(modules_list)} 个模块",
            "stream_events": [{
                "event_type": "module",
                "agent": "content_orchestrator",
                "data": result,
                "step_description": f"内容编排完成，共 {len(modules_list)} 个模块"
            }],
        }

    except Exception as e:
        logger.error(f"  [内容编排智能体] 编排失败: {str(e)}")
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
