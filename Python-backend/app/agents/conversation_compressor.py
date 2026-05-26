"""
会话压缩智能体 - 对早期对话进行关键信息提取和压缩
作为后台异步任务执行，不阻塞主流程
"""
import logging
import json
from typing import Dict, Any, List, Optional
from app.agents.llm_factory import get_compressor_llm
from app.services.db.java_client import java_client

logger = logging.getLogger("agents.conversation_compressor")

SYSTEM_PROMPT = """你是一个对话压缩专家。你的任务是将多轮对话压缩为简洁的上下文摘要，保留关键信息的同时大幅减少 token 数量。

## 压缩规则

### 必须保留的信息
- 用户提到的实体（人名、技术名词、项目名、概念等）
- 关键事实和数据
- 用户的决策和选择
- 用户的意图和目标
- AI 给出的重要结论或建议
- 未解决的问题或待办事项

### 必须删除的信息
- 重复出现的内容
- 寒暄和客套话
- 无关紧要的过渡语句
- 已在后续对话中被明确或修正的信息
- AI 的通用解释（非针对用户特定情况的）

### 输出要求
- 用简洁的第三人称叙述，不要用对话格式
- 按主题组织信息，不要按对话轮次
- 输出纯文本，不要用 Markdown 格式
- 控制在 300 字以内

## 输出格式
严格输出 JSON：
{
  "summary": "压缩后的上下文摘要"
}"""


def compress_dialogues(
    dialogues: List[Dict[str, Any]],
    existing_context: Optional[str] = None,
) -> Optional[str]:
    """
    压缩对话列表，返回压缩后的摘要文本。

    Args:
        dialogues: 要压缩的对话列表，每条包含 role 和 content
        existing_context: 之前的压缩摘要（如果有的话）

    Returns:
        压缩后的摘要文本，失败返回 None
    """
    if not dialogues:
        return existing_context

    llm = get_compressor_llm()

    # 构造对话文本
    dialogue_lines = []
    for msg in dialogues:
        role = "用户" if msg.get("role") == "user" else "助手"
        content = msg.get("content", "")[:500]  # 截断过长内容
        dialogue_lines.append(f"{role}: {content}")
    dialogue_text = "\n".join(dialogue_lines)

    # 构造用户提示
    if existing_context:
        user_prompt = f"""## 之前的上下文摘要
{existing_context}

## 需要压缩的对话（与上述摘要合并压缩）
{dialogue_text}

请将"之前的上下文摘要"和"需要压缩的对话"合并压缩为一个新的完整摘要。输出 JSON："""
    else:
        user_prompt = f"""## 需要压缩的对话
{dialogue_text}

请将以上对话压缩为简洁的上下文摘要。输出 JSON："""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = llm.chat_json(messages, max_tokens=1024)
        summary = result.get("summary", "")
        if summary:
            logger.info(f"  [会话压缩] 压缩完成，摘要长度: {len(summary)} 字符")
            return summary
        else:
            logger.warning("  [会话压缩] LLM 返回空摘要")
            return existing_context
    except Exception as e:
        logger.error(f"  [会话压缩] 压缩失败: {str(e)}")
        return existing_context


def build_chat_history_with_context(
    raw_history: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    从原始对话历史中构建带压缩上下文的 chat_history。

    查找最新的 conversation_context 不为 null 的对话，
    将压缩摘要作为 assistant 消息插入到实际对话前面。

    Args:
        raw_history: 数据库返回的原始对话历史（已按时间排序）

    Returns:
        构建好的 chat_history 列表：[压缩摘要, context之后的所有实际对话]
    """
    # 从后往前找最新的 conversation_context
    latest_context = None
    context_index = -1
    for i in range(len(raw_history) - 1, -1, -1):
        ctx = raw_history[i].get("conversationContext") or raw_history[i].get("conversation_context")
        if ctx:
            latest_context = ctx
            context_index = i
            break

    # 取 context 之后的所有实际对话
    if latest_context is not None:
        actual_dialogues = raw_history[context_index + 1:]
    else:
        actual_dialogues = raw_history

    # 构建 chat_history
    chat_history = []

    # 插入压缩摘要
    if latest_context:
        chat_history.append({
            "role": "assistant",
            "content": f"[历史对话摘要] {latest_context}",
        })

    # 插入 context 之后的所有实际对话
    for h in actual_dialogues:
        chat_history.append({
            "role": "user" if h.get("dialogueType") == "USER" else "assistant",
            "content": h.get("conversationText", ""),
        })

    return chat_history


async def async_compress_and_save(
    user_id: int,
    session_id: str,
    plan_id: int,
):
    """
    异步执行会话压缩（后台任务）。

    1. 获取完整对话历史
    2. 找到最新的 conversation_context 位置
    3. 如果从该位置到末尾 >= 20 条，触发压缩
    4. 压缩倒数第 11-20 条（+ 旧摘要），存到倒数第 10 条
    """
    try:
        logger.info(f"  [会话压缩] 开始检查用户 {user_id} 会话 {session_id}")

        # 获取完整对话历史
        history = java_client.get_dialogue_history(
            user_id=user_id, plan_id=plan_id, session_id=session_id, limit=200
        )
        if not history or len(history) < 20:
            logger.info(f"  [会话压缩] 对话不足 20 条（{len(history) or 0} 条），跳过")
            return

        # 从后往前找最新的 conversation_context
        latest_context = None
        context_index = -1
        for i in range(len(history) - 1, -1, -1):
            ctx = history[i].get("conversationContext") or history[i].get("conversation_context")
            if ctx:
                latest_context = ctx
                context_index = i
                break

        # 计算从 context 位置到末尾的对话数
        if context_index >= 0:
            count_from_context = len(history) - context_index - 1  # 不含 context 那条
        else:
            count_from_context = len(history)

        if count_from_context < 20:
            logger.info(f"  [会话压缩] 从压缩位置起不足 20 条（{count_from_context} 条），跳过")
            return

        # 需要压缩：压缩倒数第 11-20 条
        # 从 context 位置之后的实际对话中，取前 10 条
        if context_index >= 0:
            actual_dialogues = history[context_index + 1:]
        else:
            actual_dialogues = history

        # 取前 10 条压缩
        to_compress = actual_dialogues[:10]
        # 存储目标：第 11 条（actual_dialogues[10]）
        target_dialogue = actual_dialogues[10] if len(actual_dialogues) > 10 else None

        if not to_compress or not target_dialogue:
            logger.warning("  [会话压缩] 无法确定压缩范围")
            return

        target_id = target_dialogue.get("id") or target_dialogue.get("dialogueId")
        if not target_id:
            logger.warning("  [会话压缩] 无法获取目标对话 ID")
            return

        # 转换格式
        dialogue_msgs = []
        for d in to_compress:
            dialogue_msgs.append({
                "role": "user" if d.get("dialogueType") == "USER" else "assistant",
                "content": d.get("conversationText", ""),
            })

        logger.info(f"  [会话压缩] 压缩 {len(to_compress)} 条对话，存入 ID={target_id}")

        # 执行压缩
        import asyncio
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None, compress_dialogues, dialogue_msgs, latest_context
        )

        if summary:
            # 存入数据库
            await loop.run_in_executor(
                None, java_client.update_dialogue_context, target_id, summary
            )
            logger.info(f"  [会话压缩] 压缩完成并存入 ID={target_id}，摘要长度: {len(summary)}")
        else:
            logger.warning("  [会话压缩] 压缩返回空结果")

    except Exception as e:
        logger.error(f"  [会话压缩] 异步压缩失败: {str(e)}", exc_info=True)
