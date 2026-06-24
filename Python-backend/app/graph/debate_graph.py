"""
辩论子图 - 编排者与审查者通过共享消息黑板进行多轮辩论

流程：
  orchestrator → moderator → (条件路由)
                     ↓
            continue → reviewer → moderator
            resolved/max_rounds → END
"""
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agents.schemas import AgentState
from app.agents.content_orchestrator import debate_orchestrator_node
from app.agents.reviewer import debate_reviewer_node
from app.prompts import DEBATE_MODERATOR_PROMPT
from app.agents.llm_factory import get_reviewer_llm

logger = logging.getLogger("graph.debate")

NODE_DEBATE_ORCHESTRATOR = "debate_orchestrator"
NODE_DEBATE_REVIEWER = "debate_reviewer"
NODE_DEBATE_MODERATOR = "debate_moderator"

MAX_DEBATE_ROUNDS = 3


# ==================== 节点函数 ====================

def _enter_debate(state: AgentState) -> Dict[str, Any]:
    """辩论入口节点：初始化辩论轮次"""
    logger.info(f"  [辩论入口] 初始化辩论，轮次=1")
    return {
        "debate_round": 1,
        "debate_status": "ongoing",
    }


def _debate_moderator_node(state: AgentState) -> Dict[str, Any]:
    """辩论主持人：读取完整辩论历史，LLM 裁决"""
    debate_messages = state.get("debate_messages", [])
    debate_round = state.get("debate_round", 1)
    failed_modules = state.get("failed_modules", [])

    logger.info(f"{'='*60}")
    logger.info(f"  [辩论主持人] 第 {debate_round} 轮判断")
    logger.info(f"  辩论消息数: {len(debate_messages)}")

    # 轮次上限硬兜底
    if debate_round >= MAX_DEBATE_ROUNDS:
        logger.warning(f"  [辩论主持人] 达到轮次上限 {MAX_DEBATE_ROUNDS} → max_rounds")
        retry_ids = [m["module_order"] for m in failed_modules] if failed_modules else []
        return {
            "debate_status": "max_rounds",
            "debate_round": debate_round + 1,
            "retry_module_ids": retry_ids,
            "debate_messages": [{"role": "moderator", "content": f"第{debate_round}轮: 达到辩论上限({MAX_DEBATE_ROUNDS}轮)，交由主控兜底。"}],
        }

    # 构造完整对话历史供 LLM 裁决
    history_text = ""
    for msg in debate_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        history_text += f"[{role}]:\n{content}\n\n"

    messages = [
        {"role": "system", "content": DEBATE_MODERATOR_PROMPT},
        {"role": "user", "content": f"""当前轮次: 第{debate_round}轮（上限{MAX_DEBATE_ROUNDS}轮）

完整辩论历史:
{history_text}

请判断下一步："""},
    ]

    try:
        llm = get_reviewer_llm()
        result = llm.chat_json(messages, max_tokens=256)
        decision = result.get("decision", "continue")
        reason = result.get("reason", "")

        if decision not in ("continue", "resolved", "max_rounds"):
            decision = "continue"

        logger.info(f"  [辩论主持人] LLM 判断: {decision} (理由: {reason[:80]})")
        logger.info(f"{'='*60}")

        out = {
            "debate_status": decision,
            "debate_messages": [{"role": "moderator", "content": f"第{debate_round}轮裁决: {decision}。理由: {reason}"}],
        }
        if decision == "continue":
            out["debate_round"] = debate_round + 1
        elif decision == "max_rounds":
            out["retry_module_ids"] = [m["module_order"] for m in failed_modules] if failed_modules else []
        return out
    except Exception as e:
        logger.error(f"  [辩论主持人] LLM 调用失败，默认继续: {e}")
        return {
            "debate_status": "continue",
            "debate_round": debate_round + 1,
            "debate_messages": [{"role": "moderator", "content": f"第{debate_round}轮: 主持人判断异常，默认继续。"}],
        }


# ==================== 路由函数 ====================

def _route_after_moderator(state: AgentState) -> str:
    """主持人之后的路由"""
    status = state.get("debate_status", "continue")
    if status in ("resolved", "max_rounds"):
        logger.info(f"  [辩论路由] {status} → END")
        return END
    # continue → reviewer
    logger.info(f"  [辩论路由] continue → reviewer")
    return NODE_DEBATE_REVIEWER


def _route_after_orchestrator(state: AgentState) -> str:
    """编排者之后的路由 → 主持人"""
    anomaly = state.get("agent_anomaly")
    if anomaly:
        logger.warning(f"  [辩论路由] 编排者检测到异常 → END（交给父图处理）")
        return END
    return NODE_DEBATE_MODERATOR


def _route_after_reviewer(state: AgentState) -> str:
    """审查者之后的路由 → 主持人"""
    anomaly = state.get("agent_anomaly")
    if anomaly:
        logger.warning(f"  [辩论路由] 审查者检测到异常 → END（交给父图处理）")
        return END
    return NODE_DEBATE_MODERATOR


# ==================== 构建子图 ====================

def build_debate_graph() -> StateGraph:
    """构建辩论子图"""
    logger.info("正在构建辩论子图...")

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("enter_debate", _enter_debate)
    graph.add_node(NODE_DEBATE_ORCHESTRATOR, debate_orchestrator_node)
    graph.add_node(NODE_DEBATE_REVIEWER, debate_reviewer_node)
    graph.add_node(NODE_DEBATE_MODERATOR, _debate_moderator_node)

    # 入口
    graph.set_entry_point("enter_debate")

    # enter_debate → orchestrator（无条件）
    graph.add_edge("enter_debate", NODE_DEBATE_ORCHESTRATOR)

    # orchestrator → moderator 或 END（异常）
    graph.add_conditional_edges(
        NODE_DEBATE_ORCHESTRATOR,
        _route_after_orchestrator,
        {
            NODE_DEBATE_MODERATOR: NODE_DEBATE_MODERATOR,
            END: END,
        }
    )

    # moderator → reviewer 或 END
    graph.add_conditional_edges(
        NODE_DEBATE_MODERATOR,
        _route_after_moderator,
        {
            NODE_DEBATE_REVIEWER: NODE_DEBATE_REVIEWER,
            END: END,
        }
    )

    # reviewer → moderator 或 END（异常）
    graph.add_conditional_edges(
        NODE_DEBATE_REVIEWER,
        _route_after_reviewer,
        {
            NODE_DEBATE_MODERATOR: NODE_DEBATE_MODERATOR,
            END: END,
        }
    )

    logger.info("辩论子图构建完成")
    return graph


# 编译后的子图实例
_debate_graph_compiled = None


def get_debate_graph():
    """获取编译后的辩论子图"""
    global _debate_graph_compiled
    if _debate_graph_compiled is None:
        graph = build_debate_graph()
        _debate_graph_compiled = graph.compile()
    return _debate_graph_compiled
