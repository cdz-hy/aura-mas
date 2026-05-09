"""
题目判定智能体 - 重点针对简答题，评判参考答案和用户实际回答，给出分数比例
"""
import logging
from typing import Dict, Any
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_quiz_grader_llm

logger = logging.getLogger("agents.quiz_grader")

SYSTEM_PROMPT = """你是一个严格的题目批改专家。你的任务是根据参考答案评判用户的回答，给出公正准确的评分。

## 评分标准
1. **选择题/判断题**: 完全正确得1分，否则0分
2. **填空题**: 关键词匹配，部分正确可给0.5分
3. **简答题**: 按照以下维度评分
   - 核心概念准确性 (40%)
   - 逻辑完整性 (30%)
   - 表达清晰度 (15%)
   - 补充有价值的额外信息 (15%)

## 输出格式
严格输出 JSON：
{
  "score": 0.85,
  "is_correct": true,
  "feedback": "详细的批改反馈",
  "key_points_hit": ["命中的要点1"],
  "key_points_missed": ["遗漏的要点1"],
  "improvement_suggestions": ["改进建议1"]
}

## 规则
- score 为 0-1 之间的浮点数
- is_correct: score >= 0.6 为 true
- 严禁使用 emoji 表情符号
- 反馈要具体、有建设性"""


def quiz_grader_node(state: AgentState) -> Dict[str, Any]:
    """题目判定智能体节点"""
    quiz_answer = state.get("quiz_answer", "")
    quiz_questions = state.get("quiz_questions", [])
    user_message = state.get("user_message", "")

    logger.info(f"{'='*60}")
    logger.info(f"  [题目判定智能体] 开始处理")
    logger.info(f"  待批改题目数: {len(quiz_questions) if quiz_questions else 0}")

    if not quiz_questions:
        logger.warning(f"  [题目判定智能体] 无待批改题目")
        logger.info(f"{'='*60}")
        return {
            "quiz_result": {"score": 0, "is_correct": False, "feedback": "没有待批改的题目"},
            "current_step": "题目判定智能体: 无待批改题目",
        }

    llm = get_quiz_grader_llm()

    target_question = quiz_questions[0]
    correct_answer = target_question.get("correct_answer", "")
    question_text = target_question.get("question_text", "")
    question_type = target_question.get("question_type", "")
    explanation = target_question.get("explanation", "")

    answer = quiz_answer or user_message

    logger.info(f"  [题目判定智能体] 题目: {question_text[:80]}")
    logger.info(f"  [题目判定智能体] 题型: {question_type}")
    logger.info(f"  [题目判定智能体] 用户答案: {answer[:100]}")
    logger.info(f"  [题目判定智能体] 参考答案: {correct_answer[:100]}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""题目: {question_text}
题型: {question_type}
参考答案: {correct_answer}
答案解析: {explanation}

用户回答: {answer}

请批改并输出 JSON:"""}
    ]

    try:
        logger.info(f"  [题目判定智能体] 正在调用 LLM 进行批改...")
        result = llm.chat_json(messages, max_tokens=2048)
        score = result.get("score", 0)
        is_correct = result.get("is_correct", False)
        feedback = result.get("feedback", "")
        hit = result.get("key_points_hit", [])
        missed = result.get("key_points_missed", [])

        logger.info(f"  [题目判定智能体] 批改完成!")
        logger.info(f"    得分: {score:.0%}")
        logger.info(f"    结果: {'正确' if is_correct else '不正确'}")
        logger.info(f"    命中要点: {', '.join(hit)}")
        logger.info(f"    遗漏要点: {', '.join(missed)}")
        logger.info(f"    反馈: {feedback[:150]}")
        logger.info(f"{'='*60}")

        return {
            "quiz_result": {
                "score": score,
                "is_correct": is_correct,
                "feedback": feedback,
                "key_points_hit": hit,
                "key_points_missed": missed,
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "question_text": question_text,
                "correct_answer": correct_answer,
                "user_answer": answer,
            },
            "current_step": f"题目判定智能体: 得分 {score:.0%}, {'正确' if is_correct else '不正确'}",
            "stream_events": [{
                "event_type": "quiz_result",
                "agent": "quiz_grader",
                "data": result,
                "step_description": f"批改完成: 得分 {score:.0%}"
            }],
        }

    except Exception as e:
        logger.error(f"  [题目判定智能体] 批改异常: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "quiz_result": {"score": 0, "is_correct": False, "feedback": f"批改异常: {str(e)}"},
            "current_step": f"题目判定智能体: 批改异常 - {str(e)}",
            "stream_events": [{
                "event_type": "error",
                "agent": "quiz_grader",
                "data": {"error": str(e)},
                "step_description": "批改异常"
            }],
        }
