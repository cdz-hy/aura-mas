"""
题目判定智能体 - 重点针对简答题，评判参考答案和用户实际回答，给出分数比例
"""
import logging
from typing import Dict, Any
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_quiz_grader_llm
from app.prompts import QUIZ_GRADER_PROMPT
from app.utils.token_recorder import record_from_mimo
from app.utils import stream_registry
import json

logger = logging.getLogger("agents.quiz_grader")



def quiz_grader_node(state: AgentState) -> Dict[str, Any]:
    """题目判定智能体节点"""
    quiz_answer = state.get("quiz_answer", "")
    quiz_questions = state.get("quiz_questions", [])
    user_message = state.get("user_message", "")

    logger.info(f"{'='*60}")
    logger.info(f"  [题目判定智能体] 开始处理")
    logger.info(f"  待批改题目数: {len(quiz_questions) if quiz_questions else 0}")

    # 实时推送思考过程
    _sse_cb = state.get("sse_callback") or stream_registry.get_sse_callback(state.get("session_id", ""))

    def _emit_thinking(content: str):
        if _sse_cb:
            try:
                _sse_cb(f'data: {json.dumps({"type": "thinking", "agent": "题目判定智能体", "content": content}, ensure_ascii=False)}\n\n')
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

    _emit_thinking("正在批改你的答案...")

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
        {"role": "system", "content": QUIZ_GRADER_PROMPT},
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
        record_from_mimo(llm, state.get("user_id", 0), "quiz_grading", state.get("task_id"))
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
