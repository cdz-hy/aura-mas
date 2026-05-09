"""
题目生成智能体 - 结合用户画像中的薄弱点和偏好题型，自主抉择题目类型并生成题目
可选择调用 RAG 检索相关知识点结合内容生成
"""
import logging
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_quiz_generator_llm

logger = logging.getLogger("agents.quiz_generator")

SYSTEM_PROMPT = """你是一个专业的题目出题专家。根据学习内容和用户画像，生成高质量的练习题目。

## 题目类型
- single_choice: 单选题（4个选项）
- multiple_choice: 多选题（4-5个选项）
- true_false: 判断题
- fill_blank: 填空题
- short_answer: 简答题

## 出题规则
1. 根据用户偏好题型和薄弱点重点出题
2. 难度要适当，不要过难或过简
3. 题目要覆盖关键知识点
4. 每道题都要有详细的答案解析
5. 选择题的干扰项要合理

## 输出格式
严格输出 JSON：
{
  "quiz_title": "测验标题",
  "description": "测验说明",
  "questions": [
    {
      "question_id": 1,
      "question_type": "single_choice",
      "difficulty": 3,
      "knowledge_point": "对应知识点",
      "question_text": "题目内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "correct_answer": "A",
      "explanation": "详细解析"
    }
  ],
  "total_questions": 5,
  "difficulty_distribution": {"easy": 2, "medium": 2, "hard": 1}
}

## 规则
- 严禁使用 emoji 表情符号
- 所有文本使用中文
- 题目数量默认5道，根据内容量可适当增减"""


def quiz_generator_node(state: AgentState) -> Dict[str, Any]:
    """题目生成智能体节点"""
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    rag_chunks = state.get("rag_context_chunks", [])
    user_profile = state.get("user_profile", {})
    orchestrated_content = state.get("orchestrated_content")

    logger.info(f"{'='*60}")
    logger.info(f"  [题目生成智能体] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")

    llm = get_quiz_generator_llm()

    behavior = user_profile.get("learning_behavior", {})
    weak_points = behavior.get("weak_points", [])
    pref_types = behavior.get("preferred_quiz_types", [])

    if weak_points:
        logger.info(f"  [题目生成智能体] 用户薄弱点: {', '.join(weak_points)}")
    if pref_types:
        logger.info(f"  [题目生成智能体] 偏好题型: {', '.join(pref_types)}")

    content_summary = ""
    if orchestrated_content:
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

    pref_text = f"偏好题型: {', '.join(pref_types)}" if pref_types else "无特殊偏好"
    weak_text = f"薄弱知识点: {', '.join(weak_points)}" if weak_points else "暂无薄弱点记录"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

学习内容摘要:
{content_summary}

{pref_text}
{weak_text}

请根据以上信息生成练习题目，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [题目生成智能体] 正在调用 LLM 生成题目...")
        result = llm.chat_json(messages, max_tokens=4096)
        questions = result.get("questions", [])

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

        return {
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
