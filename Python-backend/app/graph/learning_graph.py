"""
LangGraph 多智能体工作流图 - 个性化学习资源生成系统
"""
import logging
import asyncio
from typing import Dict, Any, List, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.schemas import (
    AgentState,
    NODE_CONTROLLER, NODE_TASK_DECOMPOSER, NODE_SIMPLE_ANSWER,
    NODE_RAG_RETRIEVER, NODE_RESOURCE_GENERATOR, NODE_QUIZ_GENERATOR,
    NODE_QUIZ_GRADER, NODE_RESOURCE_TYPE_GENERATOR,
    NODE_ANIMATION_SKILL_GENERATOR,
    NODE_PROFILE_MAINTAINER, NODE_HUMAN_CONFIRM,
    NODE_REVIEW_ORCHESTRATE, NODE_REVIEWER, NODE_CONTENT_ORCHESTRATOR,
    NODE_WAIT_USER_REPLY,
    INTENT_GENERATE_RESOURCE, INTENT_SIMPLE_QA, INTENT_GENERATE_QUIZ,
    INTENT_GRADE_QUIZ, INTENT_AMBIGUOUS, INTENT_FOLLOW_UP, INTENT_CLARIFY,
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
from app.agents.resource_type_generator import resource_type_generator_node
from app.agents.animation_skill_generator import animation_skill_generator_node
from app.agents.profile_maintainer import profile_maintainer_node
from app.services.db.java_client import java_client

logger = logging.getLogger("graph.learning")


# ==================== 路由函数 ====================

def _route_if_anomaly(state: AgentState) -> str | None:
    """如果智能体报告了异常，统一路由回主控"""
    if state.get("agent_anomaly"):
        logger.warning(f"  [路由] 智能体报告异常: {state.get('anomaly_reason', '')} -> 回到主控")
        return NODE_CONTROLLER
    return None


def route_after_controller(state: AgentState) -> str:
    """主控智能体之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    next_node = state.get("next_node", NODE_SIMPLE_ANSWER)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 15)

    if iteration >= max_iter:
        logger.warning(f"  [路由] 达到最大迭代次数 {max_iter}，强制结束")
        return END

    logger.info(f"  [路由] 主控 -> {next_node}")
    return next_node


def route_after_animation_skill_generator(state: AgentState) -> str:
    """动画生成之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly
    error = state.get("error")
    if error:
        logger.info(f"  [路由] 动画生成失败 -> END")
    return END


def route_after_rag(state: AgentState) -> str | List[str]:
    """RAG 检索之后的路由 - 决定并行或串行分支"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    rag_sufficient = state.get("rag_sufficient", False)
    if not rag_sufficient:
        logger.info(f"  [路由] RAG 检索不足 (低分/无关内容已过滤) -> 资源自主生成智能体")
        return NODE_RESOURCE_GENERATOR

    # 自主生成内容存在时，必须走串行：先编排后审查
    generated_content = state.get("generated_content")
    if generated_content:
        logger.info(f"  [路由] 自主生成模式: 先编排 -> 后审查 (串行路由)")
        return NODE_CONTENT_ORCHESTRATOR

    # 正常模式：并行分支到编排和审查
    logger.info(f"  [路由] RAG 检索完成 -> 编排与审查 (并行路由)")
    return [NODE_CONTENT_ORCHESTRATOR, NODE_REVIEWER]


def route_after_content_orchestrator(state: AgentState) -> str:
    """内容编排之后的路由 - 并行模式下汇合，自主生成/重试模式下流向审查"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    # 自主生成模式或重试模式：串行路由流向审查智能体
    if state.get("generated_content") or state.get("retry_mode"):
        logger.info(f"  [路由] 串行模式: 编排完成 -> 审查智能体")
        return NODE_REVIEWER

    # 正常并行模式：直接流向汇合节点
    logger.info(f"  [路由] 并行模式: 编排完成 -> 审查编排汇合")
    return NODE_REVIEW_ORCHESTRATE


def route_after_reviewer(state: AgentState) -> str:
    """审查智能体之后的路由 -> 审查编排汇合"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    logger.info(f"  [路由] 审查完成 -> 审查编排汇合")
    return NODE_REVIEW_ORCHESTRATE


def route_after_review_orchestrate(state: AgentState) -> str:
    """审查编排并行之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

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
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    profile_update_needed = state.get("profile_update_needed", False)
    rag_sufficient = state.get("rag_sufficient", True)
    intent = state.get("intent", "")
    
    # 优先处理画像更新
    if profile_update_needed:
        logger.info(f"  [路由] 简答完成 -> END (画像维护将在后台异步执行)")
        return END
    
    # RAG 无结果 + 资源生成意图 -> 资源自主生成
    if not rag_sufficient and intent == INTENT_GENERATE_RESOURCE:
        logger.info(f"  [路由] RAG 无结果 + 资源生成意图 -> 资源自主生成智能体")
        return NODE_RESOURCE_GENERATOR
    
    # 默认结束
    logger.info(f"  [路由] 简答完成 -> END")
    return END


def route_after_task_decomposer(state: AgentState) -> str:
    """任务分解之后的路由 - 根据是否需要分解决定是否走确认流程"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    task_breakdown = state.get("task_breakdown") or {}
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
    """用户确认之后的路由

    优先级：确认 > 反馈 > 等待
    确认时 human_feedback 可能残留（_human_confirm_node 不清除），需先检查 confirmed
    """
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    task_breakdown = state.get("task_breakdown")
    human_feedback = state.get("human_feedback")

    # 优先：用户已确认任务分解 → 直接进入 RAG 检索（跳过 Controller）
    if task_breakdown and state.get("task_breakdown_confirmed"):
        logger.info(f"  [路由] 用户已确认 -> RAG 检索智能体")
        return NODE_RAG_RETRIEVER

    if human_feedback:
        logger.info(f"  [路由] 用户有反馈 -> 主控智能体 (重新判断)")
        return NODE_CONTROLLER

    # 没有反馈且未确认 -> 结束流程，等待用户通过 /confirm 接口重新进入
    logger.info(f"  [路由] 等待用户确认 -> END (等待用户通过 /confirm 接口输入)")
    return END


def route_after_quiz_generator(state: AgentState) -> str:
    """题目生成之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    if state.get("_detected_quiz_requirements"):
        logger.info(f"  [路由] 题目生成完成 + 检测到专门要求 -> 进入画像维护")
        return NODE_PROFILE_MAINTAINER

    logger.info(f"  [路由] 题目生成完成 -> END")
    return END


def route_after_resource_type_generator(state: AgentState) -> str:
    """类型资源生成之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    error = state.get("error")
    if error:
        logger.info(f"  [路由] 类型资源生成失败 -> END")
    else:
        logger.info(f"  [路由] 类型资源生成完成 -> END")
    return END


def route_after_quiz_grader(state: AgentState) -> str:
    """题目判定之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    # 题目判定完成 → 结束流程 (画像维护将在后台异步执行)
    logger.info(f"  [路由] 题目判定完成 -> END (画像维护将在后台异步执行)")
    return END


def route_after_resource_generator(state: AgentState) -> str:
    """自主生成之后的路由 -> 直接结束（网络资源跳过审查）"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    logger.info(f"  [路由] 资源自主生成完成 -> END")
    return END


def route_after_profile_maintainer(state: AgentState) -> str:
    """画像维护之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly

    logger.info(f"  [路由] 画像维护完成 -> END")
    return END


# ==================== 审查编排并行汇合节点 ====================

def review_orchestrate_node(state: AgentState) -> Dict[str, Any]:
    """
    审查与编排 Join 汇合节点
    根据上游并行的 Reviewer 和 Content Orchestrator 结果进行合并与决策
    """
    logger.info(f"{'='*60}")
    logger.info(f"  [审查编排汇合节点] 开始合并结果")

    error = state.get("error")
    if error:
        logger.error(f"  [审查编排汇合节点] 检测到上游执行错误: {error}")
        return {
            "current_step": "审查编排汇合节点: 检测到上游执行错误",
        }

    # 传播子智能体的异常信号
    if state.get("agent_anomaly"):
        logger.warning(f"  [审查编排汇合节点] 上游智能体报告异常，向上传播")
        return {}

    review_passed = state.get("review_passed", True)
    review_feedback = state.get("review_feedback", "")
    review_suggestions = state.get("review_suggestions", [])
    module_list = state.get("module_list", [])
    orchestrated_content = state.get("orchestrated_content")

    # 审查未通过 → 保留已通过模块的编排结果，只重试未通过的模块
    if not review_passed:
        logger.warning(f"  [审查编排汇合节点] 审查未通过")

        failed_modules = state.get("failed_modules", [])
        passed_modules = state.get("passed_modules", [])
        retry_ids = [m["module_order"] for m in failed_modules] if failed_modules else []

        # 从编排结果中提取已通过模块的内容（保留下来，不走重试）
        passed_orchestrated = [
            m for m in module_list
            if m.get("module_order") not in retry_ids
        ]

        if retry_ids:
            logger.warning(f"  [审查编排汇合节点] 需要重新生成的模块: {retry_ids}")
            logger.info(f"  [审查编排汇合节点] 保留已通过模块 {len(passed_orchestrated)} 个，只重试 {len(retry_ids)} 个")
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
            # 保留完整的模块列表（包含通过和未通过的），供重试时合并使用
            "module_list": module_list,
            "orchestrated_content": {
                "title": orchestrated_content.get("title", "") if orchestrated_content else "",
                "modules": passed_orchestrated,
            } if passed_orchestrated else None,
            # 立即通知前端已通过的模块（可提前展示）
            "passed_module_list": passed_orchestrated,
            "error": f"内容审查未通过: {review_feedback}",
            "current_step": f"审查编排汇合节点: 审查未通过 - {review_feedback[:80]} (重试 {len(retry_ids)} 个模块)",
        }

    # 审查通过 + 编排成功 → 合并结果
    logger.info(f"  [审查编排汇合节点] 审查通过，编排完成")
    logger.info(f"    编排标题: {orchestrated_content.get('title', '未命名') if orchestrated_content else '未命名'}")
    logger.info(f"    模块数: {len(module_list)}")
    logger.info(f"{'='*60}")

    return {
        "orchestrated_content": orchestrated_content,
        "module_list": module_list,
        "review_passed": True,
        "review_feedback": review_feedback,
        "review_suggestions": review_suggestions,
        "error": None,  # 显式清除 error，防止上一次迭代的残留值导致路由误判
        "current_step": "审查编排完成",
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
    graph.add_node(NODE_CONTENT_ORCHESTRATOR, content_orchestrator_node)
    graph.add_node(NODE_REVIEWER, reviewer_node)
    graph.add_node(NODE_REVIEW_ORCHESTRATE, review_orchestrate_node)
    graph.add_node(NODE_RESOURCE_GENERATOR, resource_generator_node)
    graph.add_node(NODE_QUIZ_GENERATOR, quiz_generator_node)
    graph.add_node(NODE_QUIZ_GRADER, quiz_grader_node)
    graph.add_node(NODE_RESOURCE_TYPE_GENERATOR, resource_type_generator_node)
    graph.add_node(NODE_ANIMATION_SKILL_GENERATOR, animation_skill_generator_node)
    graph.add_node(NODE_PROFILE_MAINTAINER, profile_maintainer_node)
    graph.add_node(NODE_HUMAN_CONFIRM, _human_confirm_node)
    graph.add_node(NODE_WAIT_USER_REPLY, wait_user_reply_node)
    logger.info("已注册 15 个节点")

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
            NODE_RESOURCE_TYPE_GENERATOR: NODE_RESOURCE_TYPE_GENERATOR,
            NODE_ANIMATION_SKILL_GENERATOR: NODE_ANIMATION_SKILL_GENERATOR,
            NODE_HUMAN_CONFIRM: NODE_HUMAN_CONFIRM,
            NODE_WAIT_USER_REPLY: NODE_WAIT_USER_REPLY,
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
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
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

    # 追问挂起 -> 回到主控继续 ReAct
    graph.add_edge(NODE_WAIT_USER_REPLY, NODE_CONTROLLER)

    # RAG 检索 -> 编排与审查分支（或资源自主生成）
    graph.add_conditional_edges(
        NODE_RAG_RETRIEVER,
        route_after_rag,
        {
            NODE_CONTENT_ORCHESTRATOR: NODE_CONTENT_ORCHESTRATOR,
            NODE_REVIEWER: NODE_REVIEWER,
            NODE_RESOURCE_GENERATOR: NODE_RESOURCE_GENERATOR,
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
        }
    )

    # 内容编排 -> 审查智能体（串行）或 审查编排汇合节点（并行）
    graph.add_conditional_edges(
        NODE_CONTENT_ORCHESTRATOR,
        route_after_content_orchestrator,
        {
            NODE_REVIEWER: NODE_REVIEWER,
            NODE_REVIEW_ORCHESTRATE: NODE_REVIEW_ORCHESTRATE,
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
        }
    )

    # 审查智能体 -> 审查编排汇合节点
    graph.add_conditional_edges(
        NODE_REVIEWER,
        route_after_reviewer,
        {
            NODE_REVIEW_ORCHESTRATE: NODE_REVIEW_ORCHESTRATE,
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
        }
    )

    # 审查编排汇合 -> 画像维护、回到主控或结束
    graph.add_conditional_edges(
        NODE_REVIEW_ORCHESTRATE,
        route_after_review_orchestrate,
        {
            NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER,
            NODE_CONTROLLER: NODE_CONTROLLER,
            END: END,
        }
    )

    # 简答 -> 结束、画像维护、自主生成、或异常回主控
    graph.add_conditional_edges(
        NODE_SIMPLE_ANSWER,
        route_after_simple_answer,
        {
            NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER,
            NODE_RESOURCE_GENERATOR: NODE_RESOURCE_GENERATOR,
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
            END: END,
        }
    )

    # 题目生成 -> 结束或异常回主控
    graph.add_conditional_edges(
        NODE_QUIZ_GENERATOR,
        route_after_quiz_generator,
        {
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
            END: END,
        }
    )

    # 类型资源生成 -> 结束或异常回主控
    graph.add_conditional_edges(
        NODE_RESOURCE_TYPE_GENERATOR,
        route_after_resource_type_generator,
        {
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
            END: END,
        }
    )

    # 动画生成 -> 结束或回主控
    graph.add_conditional_edges(
        NODE_ANIMATION_SKILL_GENERATOR,
        route_after_animation_skill_generator,
        {
            NODE_CONTROLLER: NODE_CONTROLLER,
            END: END,
        }
    )

    graph.add_conditional_edges(
        NODE_QUIZ_GRADER,
        route_after_quiz_grader,
        {
            NODE_PROFILE_MAINTAINER: NODE_PROFILE_MAINTAINER,
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
            END: END,
        }
    )

    # 自主生成 -> 直接结束或异常回主控（网络资源跳过审查）
    graph.add_conditional_edges(
        NODE_RESOURCE_GENERATOR,
        route_after_resource_generator,
        {
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
            END: END,
        }
    )

    # 画像维护 -> 结束或异常回主控
    graph.add_conditional_edges(
        NODE_PROFILE_MAINTAINER,
        route_after_profile_maintainer,
        {
            NODE_CONTROLLER: NODE_CONTROLLER,  # 异常回主控
            END: END,
        }
    )

    logger.info("工作流图构建完成")
    return graph


# ==================== 人工确认节点 ====================

def _human_confirm_node(state: AgentState) -> Dict[str, Any]:
    """人工确认节点 - 暂停图执行，等待用户确认或补充"""
    task_breakdown_confirmed = state.get("task_breakdown_confirmed", False)
    human_feedback = state.get("human_feedback")

    logger.info(f"  [人工确认节点] 开始处理")
    logger.info(f"    确认状态: {task_breakdown_confirmed}, 反馈: {human_feedback[:50] if human_feedback else '无'}")

    if task_breakdown_confirmed:
        logger.info(f"  [人工确认节点] 用户已确认学习路径")
        return {
            "needs_human_confirm": False,
            "human_feedback": None,  # 清除反馈，防止残留影响路由
            "current_step": "用户已确认学习路径",
        }
    elif human_feedback is not None:
        logger.info(f"  [人工确认节点] 用户补充说明: {human_feedback[:80]}")
        return {
            "task_breakdown_confirmed": False,
            "needs_human_confirm": False,
            "current_step": f"用户补充说明: {human_feedback[:50]}",
        }

    logger.info(f"  [人工确认节点] 等待用户确认，流程暂停")
    return {
        "current_step": "等待用户确认学习路径",
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


# ==================== 追问挂起节点 ====================

def wait_user_reply_node(state: AgentState) -> Dict[str, Any]:
    """追问挂起节点 - 用于主控 ReAct 过程中需要追问用户时暂停图执行"""
    logger.info(f"  [追问挂起节点] 等待用户回复追问内容，流程暂停")
    return {
        "current_step": "等待用户回复追问内容",
        "iteration_count": state.get("iteration_count", 0) + 1,
    }

# ==================== 全局图实例与编译 ====================
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

class FilteredSerializer:
    """过滤序列化器，用于在持久化时自动剥离函数、回调等不可序列化的对象"""
    def __init__(self):
        self.underlying = JsonPlusSerializer()

    def _filter_dict(self, obj):
        if callable(obj):
            return None
        elif isinstance(obj, dict):
            return {k: self._filter_dict(v) for k, v in obj.items() if not callable(v) and not callable(k)}
        elif isinstance(obj, list):
            return [self._filter_dict(x) for x in obj]
        elif isinstance(obj, tuple):
            return tuple(self._filter_dict(x) for x in obj)
        return obj

    def dumps(self, obj):
        return self.underlying.dumps(self._filter_dict(obj))

    def loads(self, *args, **kwargs):
        return self.underlying.loads(*args, **kwargs)

    def dumps_typed(self, obj):
        return self.underlying.dumps_typed(self._filter_dict(obj))

    def loads_typed(self, *args, **kwargs):
        return self.underlying.loads_typed(*args, **kwargs)

_learning_graph = None
_checkpointer = MemorySaver(serde=FilteredSerializer())


def get_learning_graph():
    """获取全局工作流图实例（带 Checkpointer 编译，支持原生挂起）"""
    global _learning_graph
    if _learning_graph is None:
        graph = build_learning_graph()
        _learning_graph = graph.compile(
            checkpointer=_checkpointer,
            interrupt_before=[NODE_HUMAN_CONFIRM, NODE_WAIT_USER_REPLY]
        )
    return _learning_graph
