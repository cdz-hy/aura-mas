"""
LangGraph 多智能体工作流图 - 个性化学习资源生成系统
"""
import logging
from typing import Dict, Any, List, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import StateGraph, END
from app.agents.schemas import (
    AgentState,
    NODE_CONTROLLER, NODE_TASK_DECOMPOSER, NODE_SIMPLE_ANSWER,
    NODE_RAG_RETRIEVER, NODE_RESOURCE_GENERATOR, NODE_QUIZ_GENERATOR,
    NODE_QUIZ_GRADER, NODE_PROFILE_MAINTAINER, NODE_HUMAN_CONFIRM,
    NODE_REVIEW_ORCHESTRATE,
    INTENT_GENERATE_RESOURCE, INTENT_SIMPLE_QA, INTENT_GENERATE_QUIZ,
    INTENT_GRADE_QUIZ, INTENT_AMBIGUOUS, INTENT_FOLLOW_UP,
)
from app.agents.controller import controller_node
from app.agents.task_decomposer import task_decomposer_node
from app.agents.simple_answer import simple_answer_node
from app.agents.rag_retriever import rag_retriever_node
from app.agents.content_orchestrator import content_orchestrator_node
from app.agents.reviewer import reviewer_node
from app.agents.resource_generator import resource_generator_node
from app.agents.quiz_generator import quiz_generator_node
from app.agents.quiz_grader import quiz_grader_node
from app.agents.profile_maintainer import profile_maintainer_node
from app.services.db.java_client import java_client

logger = logging.getLogger("graph.learning")


# ==================== 路由函数 ====================

def route_after_controller(state: AgentState) -> str:
    """主控智能体之后的路由"""
    next_node = state.get("next_node", NODE_SIMPLE_ANSWER)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 15)

    if iteration >= max_iter:
        logger.warning(f"  [路由] 达到最大迭代次数 {max_iter}，强制结束")
        return END

    logger.info(f"  [路由] 主控 -> {next_node}")
    return next_node


def route_after_rag(state: AgentState) -> str:
    """RAG 检索之后的路由 - 审查与编排并行"""
    rag_sufficient = state.get("rag_sufficient", False)
    if not rag_sufficient:
        logger.info(f"  [路由] RAG 检索不足 -> 简答智能体")
        return NODE_SIMPLE_ANSWER
    logger.info(f"  [路由] RAG 检索完成 -> 审查编排并行节点")
    return NODE_REVIEW_ORCHESTRATE


def route_after_review_orchestrate(state: AgentState) -> str:
    """审查编排并行之后的路由"""
    error = state.get("error")
    if error:
        logger.warning(f"  [路由] 审查编排未通过 -> 主控智能体 (重新决策)")
        return NODE_CONTROLLER
    review_passed = state.get("review_passed", True)
    if not review_passed:
        logger.warning(f"  [路由] 审查未通过 -> 主控智能体 (重新决策)")
        return NODE_CONTROLLER
    logger.info(f"  [路由] 审查编排完成 -> 画像维护智能体")
    return NODE_PROFILE_MAINTAINER


def route_after_simple_answer(state: AgentState) -> str:
    """简答之后的路由"""
    profile_update_needed = state.get("profile_update_needed", False)
    rag_sufficient = state.get("rag_sufficient", True)
    intent = state.get("intent", "")
    if not rag_sufficient and intent == INTENT_GENERATE_RESOURCE:
        logger.info(f"  [路由] RAG 无结果 + 资源生成意图 -> 资源自主生成智能体")
        return NODE_RESOURCE_GENERATOR
    if profile_update_needed:
        logger.info(f"  [路由] 需要画像更新 -> 画像维护智能体")
        return NODE_PROFILE_MAINTAINER
    logger.info(f"  [路由] 简答完成 -> END")
    return END


def route_after_task_decomposer(state: AgentState) -> str:
    """任务分解之后的路由 - 需要用户确认"""
    logger.info(f"  [路由] 任务分解完成 -> 用户确认")
    return NODE_HUMAN_CONFIRM


def route_after_human_confirm(state: AgentState) -> str:
    """用户确认之后的路由"""
    human_feedback = state.get("human_feedback")
    task_breakdown = state.get("task_breakdown")

    if human_feedback:
        logger.info(f"  [路由] 用户有反馈 -> 主控智能体 (重新判断)")
        return NODE_CONTROLLER

    if task_breakdown and state.get("task_breakdown_confirmed"):
        logger.info(f"  [路由] 用户已确认 -> RAG 检索智能体")
        return NODE_RAG_RETRIEVER

    # 没有反馈且未确认 -> 结束流程，等待用户通过 /confirm 接口重新进入
    logger.info(f"  [路由] 等待用户确认 -> END (等待用户通过 /confirm 接口输入)")
    return END


def route_after_quiz_generator(state: AgentState) -> str:
    """题目生成之后的路由"""
    logger.info(f"  [路由] 题目生成完成 -> END")
    return END


def route_after_quiz_grader(state: AgentState) -> str:
    """题目判定之后的路由"""
    logger.info(f"  [路由] 题目判定完成 -> 画像维护智能体")
    return NODE_PROFILE_MAINTAINER


def route_after_resource_generator(state: AgentState) -> str:
    """自主生成之后的路由"""
    logger.info(f"  [路由] 资源自主生成完成 -> 审查编排并行节点")
    return NODE_REVIEW_ORCHESTRATE


def route_after_profile_maintainer(state: AgentState) -> str:
    """画像维护之后的路由"""
    logger.info(f"  [路由] 画像维护完成 -> END")
    return END


# ==================== 审查编排并行节点 ====================

def review_and_orchestrate_node(state: AgentState) -> Dict[str, Any]:
    """审查与编排并行执行节点 - 两者同时启动，审查不通过则丢弃编排结果"""
    logger.info(f"{'='*60}")
    logger.info(f"  [审查编排节点] 开始并行处理")

    stream_events = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        review_future = executor.submit(reviewer_node, state)
        orchestrate_future = executor.submit(content_orchestrator_node, state)

        review_result = review_future.result()
        orchestrate_result = orchestrate_future.result()

    # 收集审查事件
    review_events = review_result.get("stream_events", [])
    stream_events.extend(review_events)

    review_passed = review_result.get("review_passed", True)
    review_feedback = review_result.get("review_feedback", "")
    review_suggestions = review_result.get("review_suggestions", [])

    # 审查未通过 → 丢弃编排结果，返回错误让主控重试
    if not review_passed:
        logger.warning(f"  [审查编排节点] 审查未通过，丢弃编排结果")
        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": review_feedback,
            "review_suggestions": review_suggestions,
            "error": f"内容审查未通过: {review_feedback}",
            "current_step": f"审查编排节点: 审查未通过 - {review_feedback[:80]}",
            "stream_events": stream_events,
        }

    # 编排出错 → 返回错误
    orchestrate_error = orchestrate_result.get("error")
    if orchestrate_error:
        logger.error(f"  [审查编排节点] 编排出错: {orchestrate_error}")
        logger.info(f"{'='*60}")
        stream_events.extend(orchestrate_result.get("stream_events", []))
        return {
            "error": orchestrate_error,
            "current_step": f"审查编排节点: 编排出错",
            "stream_events": stream_events,
        }

    # 审查通过 + 编排成功 → 合并结果
    logger.info(f"  [审查编排节点] 审查通过，编排完成")
    logger.info(f"    编排标题: {orchestrate_result.get('orchestrated_content', {}).get('title', '未命名')}")
    logger.info(f"    模块数: {len(orchestrate_result.get('module_list', []))}")
    logger.info(f"{'='*60}")

    stream_events.extend(orchestrate_result.get("stream_events", []))

    return {
        "orchestrated_content": orchestrate_result.get("orchestrated_content"),
        "module_list": orchestrate_result.get("module_list", []),
        "review_passed": True,
        "review_feedback": review_feedback,
        "review_suggestions": review_suggestions,
        "error": None,  # 显式清除 error，防止上一次迭代的残留值导致路由误判
        "current_step": orchestrate_result.get("current_step", "审查编排完成"),
        "stream_events": stream_events,
    }


# ==================== 构建工作流图 ====================

def build_learning_graph() -> StateGraph:
    """构建 LangGraph 工作流图"""
    logger.info("正在构建 LangGraph 工作流图...")

    graph = StateGraph(AgentState)

    # 注册所有节点
    graph.add_node(NODE_CONTROLLER, controller_node)
    graph.add_node(NODE_TASK_DECOMPOSER, task_decomposer_node)
    graph.add_node(NODE_SIMPLE_ANSWER, simple_answer_node)
    graph.add_node(NODE_RAG_RETRIEVER, rag_retriever_node)
    graph.add_node(NODE_REVIEW_ORCHESTRATE, review_and_orchestrate_node)
    graph.add_node(NODE_RESOURCE_GENERATOR, resource_generator_node)
    graph.add_node(NODE_QUIZ_GENERATOR, quiz_generator_node)
    graph.add_node(NODE_QUIZ_GRADER, quiz_grader_node)
    graph.add_node(NODE_PROFILE_MAINTAINER, profile_maintainer_node)
    graph.add_node(NODE_HUMAN_CONFIRM, _human_confirm_node)
    logger.info("已注册 10 个节点")

    # 设置入口
    graph.set_entry_point(NODE_CONTROLLER)

    # 主控 -> 各智能体（条件路由）
    graph.add_conditional_edges(
        NODE_CONTROLLER,
        route_after_controller,
        {
            NODE_TASK_DECOMPOSER: NODE_TASK_DECOMPOSER,
            NODE_SIMPLE_ANSWER: NODE_SIMPLE_ANSWER,
            NODE_RAG_RETRIEVER: NODE_RAG_RETRIEVER,
            NODE_QUIZ_GENERATOR: NODE_QUIZ_GENERATOR,
            NODE_QUIZ_GRADER: NODE_QUIZ_GRADER,
            NODE_RESOURCE_GENERATOR: NODE_RESOURCE_GENERATOR,
            NODE_HUMAN_CONFIRM: NODE_HUMAN_CONFIRM,
            END: END,
        }
    )

    # 任务分解 -> 用户确认
    graph.add_conditional_edges(
        NODE_TASK_DECOMPOSER,
        route_after_task_decomposer,
        {NODE_HUMAN_CONFIRM: NODE_HUMAN_CONFIRM}
    )

    # 用户确认 -> 主控或结束（等待用户通过 /confirm 接口重新进入图）
    graph.add_conditional_edges(
        NODE_HUMAN_CONFIRM,
        route_after_human_confirm,
        {
            NODE_CONTROLLER: NODE_CONTROLLER,
            NODE_RAG_RETRIEVER: NODE_RAG_RETRIEVER,
            END: END,
        }
    )

    # RAG 检索 -> 审查编排并行节点（或简答）
    graph.add_conditional_edges(
        NODE_RAG_RETRIEVER,
        route_after_rag,
        {
            NODE_REVIEW_ORCHESTRATE: NODE_REVIEW_ORCHESTRATE,
            NODE_SIMPLE_ANSWER: NODE_SIMPLE_ANSWER,
        }
    )

    # 审查编排并行 -> 画像维护或回到主控
    graph.add_conditional_edges(
        NODE_REVIEW_ORCHESTRATE,
        route_after_review_orchestrate,
        {
            NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER,
            NODE_CONTROLLER: NODE_CONTROLLER,
        }
    )

    # 简答 -> 结束、画像维护或自主生成
    graph.add_conditional_edges(
        NODE_SIMPLE_ANSWER,
        route_after_simple_answer,
        {
            NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER,
            NODE_RESOURCE_GENERATOR: NODE_RESOURCE_GENERATOR,
            END: END,
        }
    )

    # 题目生成 -> 结束
    graph.add_conditional_edges(
        NODE_QUIZ_GENERATOR,
        route_after_quiz_generator,
        {END: END}
    )

    # 题目判定 -> 画像维护
    graph.add_conditional_edges(
        NODE_QUIZ_GRADER,
        route_after_quiz_grader,
        {NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER}
    )

    # 自主生成 -> 审查编排并行节点
    graph.add_conditional_edges(
        NODE_RESOURCE_GENERATOR,
        route_after_resource_generator,
        {NODE_REVIEW_ORCHESTRATE: NODE_REVIEW_ORCHESTRATE}
    )

    # 画像维护 -> 结束
    graph.add_conditional_edges(
        NODE_PROFILE_MAINTAINER,
        route_after_profile_maintainer,
        {END: END}
    )

    logger.info("工作流图构建完成")
    return graph.compile()


# ==================== 人工确认节点 ====================

def _human_confirm_node(state: AgentState) -> Dict[str, Any]:
    """人工确认节点 - 暂停图执行，等待用户确认或补充"""
    task_breakdown = state.get("task_breakdown", {})
    human_feedback = state.get("human_feedback")

    logger.info(f"  [人工确认节点] 开始处理")
    logger.info(f"    有反馈: {'是' if human_feedback else '否'}")

    if human_feedback is not None:
        feedback_lower = human_feedback.strip().lower()
        confirm_keywords = ["确认", "可以", "没问题", "同意", "好的", "ok", "行", "嗯"]
        is_confirm = any(kw in feedback_lower for kw in confirm_keywords)

        if is_confirm:
            logger.info(f"  [人工确认节点] 用户确认学习路径")
            return {
                "task_breakdown_confirmed": True,
                "needs_human_confirm": False,
                "current_step": "用户已确认学习路径",
            }
        else:
            logger.info(f"  [人工确认节点] 用户补充说明: {human_feedback[:80]}")
            return {
                "task_breakdown_confirmed": False,
                "needs_human_confirm": False,
                "current_step": f"用户补充说明: {human_feedback[:50]}",
            }

    logger.info(f"  [人工确认节点] 等待用户确认，流程暂停")
    return {
        "needs_human_confirm": True,
        "current_step": "等待用户确认学习路径",
        "stream_events": [{
            "event_type": "confirm_needed",
            "agent": "system",
            "data": {
                "message": "学习路径已生成，请确认或补充说明",
                "task_breakdown": task_breakdown,
            },
            "step_description": "请确认学习路径规划"
        }],
        # 增加迭代计数，防止 max_iterations 检查失效
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


# ==================== 全局图实例 ====================
_learning_graph = None


def get_learning_graph():
    """获取全局工作流图实例"""
    global _learning_graph
    if _learning_graph is None:
        _learning_graph = build_learning_graph()
    return _learning_graph
