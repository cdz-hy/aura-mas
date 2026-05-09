"""
审查智能体 - 并行检查 RAG 检索内容的正确性
当有事实性和关键错误时及时切断，告知主控重新处理
目前直接调用大模型进行回答检查，后续实现 MCP 网络检索等
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_reviewer_llm

logger = logging.getLogger("agents.reviewer")

SYSTEM_PROMPT = """你是一个严格的内容审查专家。你的任务是检查 RAG 检索到的知识内容是否存在以下问题：

## 审查标准
1. **事实性错误**: 内容中的事实、数据、定义是否明显错误
2. **逻辑矛盾**: 不同来源的内容之间是否存在矛盾
3. **关键缺失**: 是否缺少关键信息导致理解偏差
4. **时效性**: 内容是否过于陈旧（如有明确的时间标记）
5. **相关性**: 检索内容与用户学习目标是否相关

## 输出要求
严格输出 JSON：
{
  "passed": true/false,
  "overall_score": 0-100,
  "issues": [
    {
      "severity": "critical/warning/info",
      "description": "问题描述",
      "source_index": 0,
      "suggestion": "修改建议"
    }
  ],
  "suggestions": ["优化建议1", "优化建议2"],
  "summary": "审查总结"
}

## 规则
- 如果存在 critical 级别的问题，passed 必须为 false
- 如果相关性低于 30 分，passed 为 false
- 严禁使用 emoji 表情符号"""


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """审查智能体节点"""
    rag_chunks = state.get("rag_context_chunks", [])
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)

    logger.info(f"{'='*60}")
    logger.info(f"  [审查智能体] 开始处理")
    logger.info(f"  待审查内容块: {len(rag_chunks)} 个")
    logger.info(f"  学习目标: {learning_goal[:100]}")

    if not rag_chunks:
        logger.warning(f"  [审查智能体] 无内容可审查")
        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": "无检索内容可供审查",
            "review_suggestions": ["重新检索"],
            "current_step": "审查智能体: 无内容可审查",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {"passed": False, "reason": "无检索内容"},
                "step_description": "审查完成：无内容可审查"
            }],
        }

    llm = get_reviewer_llm()

    content_summary = []
    for i, chunk in enumerate(rag_chunks[:15]):
        chunk_type = chunk.get("type", "text")
        heading = " > ".join(chunk.get("heading", []))
        doc_title = chunk.get("doc_title", "")
        if chunk_type == "image":
            content_summary.append(f"[{i+1}] [图片] 来源: {doc_title} | 章节: {heading} | 描述: {chunk.get('image_caption', '')[:200]}")
        else:
            content = chunk.get("content", "")[:300]
            content_summary.append(f"[{i+1}] [文本] 来源: {doc_title} | 章节: {heading} | 内容: {content}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

检索到的知识内容:
{chr(10).join(content_summary)}

请对以上内容进行审查，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [审查智能体] 正在调用 LLM 进行内容审查...")
        result = llm.chat_json(messages)
        passed = result.get("passed", True)
        issues = result.get("issues", [])
        suggestions = result.get("suggestions", [])
        summary = result.get("summary", "")
        score = result.get("overall_score", 0)

        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        warning_issues = [i for i in issues if i.get("severity") == "warning"]

        logger.info(f"  [审查智能体] 审查完成!")
        logger.info(f"    结果: {'通过' if passed else '未通过'}")
        logger.info(f"    评分: {score}/100")
        logger.info(f"    问题数: {len(issues)} (严重: {len(critical_issues)}, 警告: {len(warning_issues)})")
        for issue in issues:
            logger.info(f"      [{issue.get('severity')}] {issue.get('description', '')[:80]}")
        if suggestions:
            logger.info(f"    优化建议: {', '.join(suggestions[:3])}")
        logger.info(f"    总结: {summary[:150]}")
        logger.info(f"{'='*60}")

        return {
            "review_passed": passed,
            "review_feedback": summary,
            "review_suggestions": suggestions,
            "current_step": f"审查智能体: {'通过' if passed else '未通过'} (评分: {score}, 关键问题: {len(critical_issues)})",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {
                    "passed": passed,
                    "score": score,
                    "issues": issues,
                    "suggestions": suggestions,
                    "summary": summary,
                },
                "step_description": f"审查{'通过' if passed else '未通过'}: {summary[:100]}"
            }],
        }

    except Exception as e:
        logger.error(f"  [审查智能体] 审查异常: {str(e)}，默认通过")
        logger.info(f"{'='*60}")
        return {
            "review_passed": True,
            "review_feedback": f"审查过程异常: {str(e)}",
            "review_suggestions": [],
            "current_step": f"审查智能体: 异常({str(e)}), 默认通过",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {"passed": True, "error": str(e)},
                "step_description": "审查异常，默认通过"
            }],
        }
