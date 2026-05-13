"""
LangGraph 多智能体工作流图 - 个性化学习资源生成系统
"""
import logging
import asyncio
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
        logger.info(f"  [路由] RAG 检索不足 (低分/无关内容已过滤) -> 资源自主生成智能体")
        return NODE_RESOURCE_GENERATOR
    logger.info(f"  [路由] RAG 检索完成 -> 审查编排并行节点")
    return NODE_REVIEW_ORCHESTRATE


def route_after_review_orchestrate(state: AgentState) -> str:
    """审查编排并行之后的路由"""
    error = state.get("error")
    if error:
        logger.warning(f"  [路由] 审查编排未通过 -> 主控智能体 (重新决策)")
        return NODE_CONTROLLER
    
    review_passed = state.get("review_passed", True)
    failed_modules = state.get("failed_modules", [])
    
    # 部分模块未通过 → 标记需要重试的模块，返回主控
    if not review_passed and failed_modules:
        retry_ids = [m["module_order"] for m in failed_modules]
        logger.warning(f"  [路由] {len(failed_modules)} 个模块未通过审查 -> 主控智能体 (重新生成模块: {retry_ids})")
        return NODE_CONTROLLER
    
    # 全部未通过（RAG 审查失败）→ 返回主控
    if not review_passed:
        logger.warning(f"  [路由] 审查未通过 -> 主控智能体 (重新决策)")
        return NODE_CONTROLLER
    
    # 审查编排完成 → 直接结束（画像维护改为异步后台执行）
    logger.info(f"  [路由] 审查编排完成 -> END (画像维护将在后台异步执行)")
    return END


def route_after_simple_answer(state: AgentState) -> str:
    """简答之后的路由"""
    profile_update_needed = state.get("profile_update_needed", False)
    rag_sufficient = state.get("rag_sufficient", True)
    intent = state.get("intent", "")
    
    # 优先处理画像更新
    if profile_update_needed:
        logger.info(f"  [路由] 简答完成 -> 画像维护智能体")
        return NODE_PROFILE_MAINTAINER
    
    # RAG 无结果 + 资源生成意图 -> 资源自主生成
    if not rag_sufficient and intent == INTENT_GENERATE_RESOURCE:
        logger.info(f"  [路由] RAG 无结果 + 资源生成意图 -> 资源自主生成智能体")
        return NODE_RESOURCE_GENERATOR
    
    # 默认结束
    logger.info(f"  [路由] 简答完成 -> END")
    return END


def route_after_task_decomposer(state: AgentState) -> str:
    """任务分解之后的路由 - 根据是否需要分解决定是否走确认流程"""
    task_breakdown = state.get("task_breakdown", {})
    needs_decomposition = task_breakdown.get("needs_decomposition", True)

    if needs_decomposition:
        # 多模块 → 需要用户确认
        logger.info(f"  [路由] 多模块分解完成 -> 用户确认")
        return NODE_HUMAN_CONFIRM
    else:
        # 单模块 → 自动确认，跳过人工确认，直接进入 RAG 检索
        logger.info(f"  [路由] 单模块主题，跳过确认 -> RAG 检索")
        return NODE_RAG_RETRIEVER


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
    # 题目判定完成 → 路由到画像维护智能体
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
    """
    审查与编排节点

    优化策略：
    1. 正常模式：审查与编排并行（asyncio.gather），节省 I/O 时间
    2. 自主生成模式（有 generated_content）：先编排再审查，确保审查看到的是编排后的模块
    3. 审查不通过时丢弃编排结果（快速失败）
    """
    logger.info(f"{'='*60}")

    stream_events = []
    generated_content = state.get("generated_content")

    # 有自主生成内容时，编排器需要用 generated_content 生成模块，
    # 审查器需要看到编排后的模块 → 改为串行：先编排，再审查
    if generated_content:
        logger.info(f"  [审查编排节点] 自主生成模式: 先编排(含网络搜索内容) → 再审查")
        return _sequential_review_orchestrate(state, generated_content)

    logger.info(f"  [审查编排节点] 正常模式: 审查与编排并行")

    async def run_parallel():
        """使用 asyncio 并发执行审查和编排"""
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        # 同时启动两个任务（真正的并发）
        tasks = [
            loop.run_in_executor(None, reviewer_node, state),
            loop.run_in_executor(None, content_orchestrator_node, state),
        ]
        
        # 并发执行，同时等待两个任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results[0], results[1]  # review_result, orchestrate_result

    # 执行并发任务
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        review_result, orchestrate_result = loop.run_until_complete(run_parallel())
        loop.close()
        
        # 处理异常结果
        if isinstance(review_result, Exception):
            logger.error(f"  [审查编排节点] 审查任务异常: {str(review_result)}")
            return {
                "error": f"审查任务失败: {str(review_result)}",
                "current_step": "审查编排节点: 审查异常",
                "stream_events": stream_events,
            }
        
        if isinstance(orchestrate_result, Exception):
            logger.error(f"  [审查编排节点] 编排任务异常: {str(orchestrate_result)}")
            return {
                "error": f"编排任务失败: {str(orchestrate_result)}",
                "current_step": "审查编排节点: 编排异常",
                "stream_events": stream_events,
            }
            
    except Exception as e:
        logger.error(f"  [审查编排节点] 并行执行异常: {str(e)}")
        return {
            "error": f"审查编排并行执行失败: {str(e)}",
            "current_step": "审查编排节点: 执行异常",
            "stream_events": stream_events,
        }

    # 收集审查事件
    review_events = review_result.get("stream_events", [])
    stream_events.extend(review_events)

    review_passed = review_result.get("review_passed", True)
    review_feedback = review_result.get("review_feedback", "")
    review_suggestions = review_result.get("review_suggestions", [])

    # 审查未通过 → 保留已通过模块的编排结果，只重试未通过的模块
    if not review_passed:
        logger.warning(f"  [审查编排节点] 审查未通过")

        # 提取未通过/已通过的模块信息
        failed_modules = review_result.get("failed_modules", [])
        passed_modules = review_result.get("passed_modules", [])
        retry_ids = [m["module_order"] for m in failed_modules] if failed_modules else []

        # 从编排结果中提取已通过模块的内容（保留下来，不走重试）
        all_orchestrated_modules = orchestrate_result.get("module_list", [])
        passed_orchestrated = [
            m for m in all_orchestrated_modules
            if m.get("module_order") not in retry_ids
        ]

        if retry_ids:
            logger.warning(f"  [审查编排节点] 需要重新生成的模块: {retry_ids}")
            logger.info(f"  [审查编排节点] 保留已通过模块 {len(passed_orchestrated)} 个，只重试 {len(retry_ids)} 个")
            for m in passed_orchestrated:
                logger.info(f"      模块{m.get('module_order')} [{m.get('module_type', '')}]: {m.get('title', '')}")

        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": review_feedback,
            "review_suggestions": review_suggestions,
            "failed_modules": failed_modules,
            "passed_modules": passed_modules,
            "retry_module_ids": retry_ids,
            # 保留已通过模块的编排结果，供重试时合并
            "module_list": passed_orchestrated,
            "orchestrated_content": {
                "title": orchestrate_result.get("orchestrated_content", {}).get("title", ""),
                "modules": passed_orchestrated,
            } if passed_orchestrated else None,
            # 立即通知前端已通过的模块（可提前展示）
            "passed_module_list": passed_orchestrated,
            "error": f"内容审查未通过: {review_feedback}",
            "current_step": f"审查编排节点: 审查未通过 - {review_feedback[:80]} (重试 {len(retry_ids)} 个模块)",
            "stream_events": stream_events + ([{
                "event_type": "module",
                "agent": "content_orchestrator",
                "data": {
                    "modules": passed_orchestrated,
                    "title": orchestrate_result.get("orchestrated_content", {}).get("title", ""),
                },
                "step_description": f"审查通过 {len(passed_orchestrated)} 个模块，重试 {len(retry_ids)} 个模块"
            }] if passed_orchestrated else []),
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


# ==================== 串行审查编排（自主生成模式） ====================

def _sequential_review_orchestrate(state: AgentState, generated_content: dict) -> Dict[str, Any]:
    """
    自主生成模式：先编排(含网络搜索内容) → 再审查

    与正常并行模式不同，自主生成内容的模块需要由编排器从 generated_content 中
    提取生成，审查器必须看到编排后的 module_list 才能进行模块级别审查。
    """
    stream_events = []

    # Phase 1: 编排 — 使用 generated_content + RAG chunks 生成模块
    logger.info(f"  [审查编排节点] Phase 1: 编排(含自主生成内容)...")
    orchestrate_result = content_orchestrator_node(state)

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

    stream_events.extend(orchestrate_result.get("stream_events", []))
    module_list = orchestrate_result.get("module_list", [])

    logger.info(f"  [审查编排节点] 编排完成: {len(module_list)} 个模块")
    logger.info(f"  [审查编排节点] Phase 2: 审查编排后的模块...")

    # Phase 2: 审查 — 在编排后的模块上进行模块级别审查
    review_state = {**state}
    review_state["module_list"] = module_list

    review_result = reviewer_node(review_state)

    stream_events.extend(review_result.get("stream_events", []))

    review_passed = review_result.get("review_passed", True)
    review_feedback = review_result.get("review_feedback", "")
    review_suggestions = review_result.get("review_suggestions", [])

    # 审查未通过 → 保留已通过模块，标记未通过的供重试
    if not review_passed:
        logger.warning(f"  [审查编排节点] 审查未通过")

        failed_modules = review_result.get("failed_modules", [])
        passed_modules = review_result.get("passed_modules", [])
        retry_ids = [m["module_order"] for m in failed_modules] if failed_modules else []

        passed_orchestrated = [
            m for m in module_list
            if m.get("module_order") not in retry_ids
        ]

        if retry_ids:
            logger.warning(f"  [审查编排节点] 需要重新生成的模块: {retry_ids}")
            logger.info(f"  [审查编排节点] 保留已通过模块 {len(passed_orchestrated)} 个，重试 {len(retry_ids)} 个")

        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": review_feedback,
            "review_suggestions": review_suggestions,
            "failed_modules": failed_modules,
            "passed_modules": passed_modules,
            "retry_module_ids": retry_ids,
            "module_list": passed_orchestrated,
            "orchestrated_content": {
                "title": orchestrate_result.get("orchestrated_content", {}).get("title", ""),
                "modules": passed_orchestrated,
            } if passed_orchestrated else None,
            "passed_module_list": passed_orchestrated,
            "error": f"内容审查未通过: {review_feedback}",
            "current_step": f"审查编排节点: 审查未通过 - {review_feedback[:80]} (重试 {len(retry_ids)} 个模块)",
            "stream_events": stream_events + ([{
                "event_type": "module",
                "agent": "content_orchestrator",
                "data": {
                    "modules": passed_orchestrated,
                    "title": orchestrate_result.get("orchestrated_content", {}).get("title", ""),
                },
                "step_description": f"审查通过 {len(passed_orchestrated)} 个模块，重试 {len(retry_ids)} 个模块"
            }] if passed_orchestrated else []),
        }

    # 审查通过 + 编排成功 → 合并结果
    logger.info(f"  [审查编排节点] 审查通过，编排完成")
    logger.info(f"    编排标题: {orchestrate_result.get('orchestrated_content', {}).get('title', '未命名')}")
    logger.info(f"    模块数: {len(module_list)}")
    logger.info(f"{'='*60}")

    return {
        "orchestrated_content": orchestrate_result.get("orchestrated_content"),
        "module_list": module_list,
        "review_passed": True,
        "review_feedback": review_feedback,
        "review_suggestions": review_suggestions,
        "error": None,
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

    # 任务分解 -> 用户确认（多模块）或直接 RAG 检索（单模块）
    graph.add_conditional_edges(
        NODE_TASK_DECOMPOSER,
        route_after_task_decomposer,
        {
            NODE_HUMAN_CONFIRM: NODE_HUMAN_CONFIRM,
            NODE_RAG_RETRIEVER: NODE_RAG_RETRIEVER,
        }
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

    # RAG 检索 -> 审查编排并行节点（或资源自主生成）
    graph.add_conditional_edges(
        NODE_RAG_RETRIEVER,
        route_after_rag,
        {
            NODE_REVIEW_ORCHESTRATE: NODE_REVIEW_ORCHESTRATE,
            NODE_RESOURCE_GENERATOR: NODE_RESOURCE_GENERATOR,
        }
    )

    # 审查编排并行 -> 画像维护、回到主控或结束
    graph.add_conditional_edges(
        NODE_REVIEW_ORCHESTRATE,
        route_after_review_orchestrate,
        {
            NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER,
            NODE_CONTROLLER: NODE_CONTROLLER,
            END: END,
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
    # 注意：不返回 needs_human_confirm，避免 SSE bridge 兜底逻辑重复发送 need_confirmation
    # task_decomposer_node 已发送过 confirm_needed，路由逻辑通过 state 中已有的值判断
    return {
        "current_step": "等待用户确认学习路径",
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
