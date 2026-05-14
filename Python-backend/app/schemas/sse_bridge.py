"""
SSE 桥接层 - 将现有 LangGraph 的事件类型翻译为前端期望的 SSE 事件格式
现有 graph 输出: {event_type, agent, data, step_description}
前端期望: {type, content/dimensions/modules/...}
"""
import json
from typing import Dict, Any, List, Generator


def graph_event_to_sse(evt: Dict[str, Any]) -> str:
    """
    将 graph 节点产生的单个事件翻译为前端期望的 SSE 格式
    现有 graph 事件结构: {event_type, agent, data, step_description}
    前端 sse.ts 期望: {type, ...}
    """
    event_type = evt.get("event_type", "")
    data = evt.get("data", {})
    agent = evt.get("agent", "")

    # 映射表: graph event_type -> frontend SSE type
    if event_type == "content":
        # content 事件 -> chunk (流式文本增量)
        text = data.get("text", "")
        if text:
            return _sse({"type": "chunk", "content": text})
        return ""

    elif event_type == "thinking":
        # thinking 事件 -> progress (进度日志)
        step = data.get("step", "") or evt.get("step_description", "")
        if step:
            return _sse({"type": "progress", "content": step})
        return ""

    elif event_type == "task_breakdown":
        # task_breakdown 事件 -> modules (模块列表)
        breakdown = data.get("task_breakdown", data)
        modules = breakdown.get("modules", []) if isinstance(breakdown, dict) else []
        parts = []
        if modules:
            parts.append(_sse({"type": "modules", "data": modules}))
        # 也发送 progress
        summary = breakdown.get("summary", "") if isinstance(breakdown, dict) else ""
        if summary:
            parts.append(_sse({"type": "progress", "content": summary}))
        return "".join(parts)

    elif event_type == "module":
        # module 事件 -> modules
        # content_orchestrator 的 data 结构: {"modules": [...], "title": ...}
        # task_decomposer 的 data 结构: {"title": ..., "modules": [...], ...}
        modules = data.get("modules", [])
        if modules:
            return _sse({"type": "modules", "data": modules})
        # 单个模块对象的情况
        module_data = data.get("module", data)
        return _sse({"type": "modules", "data": [module_data]})

    elif event_type == "confirm_needed":
        # confirm_needed -> need_confirmation
        return _sse({
            "type": "need_confirmation",
            "message": data.get("message", "请确认或补充说明"),
            "task_breakdown": data.get("task_breakdown"),
        })

    elif event_type == "profile_update":
        # profile_update 直接透传
        return _sse({"type": "profile_update", "dimensions": data})

    elif event_type == "search_start":
        return _sse({"type": "progress", "content": "正在检索知识库..."})

    elif event_type == "search_results":
        count = data.get("count", 0)
        return _sse({"type": "progress", "content": f"检索完成，共找到 {count} 条相关内容"})

    elif event_type == "review":
        passed = data.get("passed", True)
        score = data.get("score", 0)
        status = "通过" if passed else "未通过"
        return _sse({"type": "progress", "content": f"内容审查: {status} (评分: {score})"})

    elif event_type == "resource_type_generated":
        # 类型资源生成完成（mindmap/summary/code 等）
        return ""  # 资源持久化由 _persist_generated_resources 处理，这里不发 SSE

    elif event_type == "quiz":
        return _sse({"type": "resource", "data": {"type": "quiz", "questions": data.get("questions", data)}})

    elif event_type == "quiz_result":
        return _sse({"type": "resource", "data": {"type": "quiz_result", "result": data}})

    elif event_type == "intent":
        intent = data.get("intent", "")
        return _sse({"type": "progress", "content": f"意图识别: {intent}"})

    elif event_type == "error":
        return _sse({"type": "error", "content": data.get("error", str(data))})

    elif event_type == "done":
        return _sse({"type": "done"})

    # 其他事件类型 -> progress
    else:
        desc = evt.get("step_description", "")
        if desc:
            return _sse({"type": "progress", "content": desc})
        return ""


def graph_step_to_sse(node_name: str, node_output: Dict[str, Any]) -> Generator[str, None, None]:
    """
    将 graph 单个节点的完整输出翻译为多条 SSE 事件
    这是主要的翻译入口，替代 agent_chat.py 中的原始输出逻辑
    """
    if node_output is None:
        return

    # 1. 处理 stream_events 列表
    has_confirm_event = False
    stream_events = node_output.get("stream_events", [])
    for evt in stream_events:
        sse = graph_event_to_sse(evt)
        if sse:
            yield sse
            if '"need_confirmation"' in sse:
                has_confirm_event = True

    # 2. 处理 current_step -> progress
    step = node_output.get("current_step", "")
    if step:
        yield _sse({"type": "progress", "content": step})

    # 3. 处理 needs_human_confirm -> need_confirmation（仅当 stream_events 中未发送过时）
    if node_output.get("needs_human_confirm") and not has_confirm_event:
        task_breakdown = node_output.get("task_breakdown")
        yield _sse({
            "type": "need_confirmation",
            "message": "请确认或补充说明学习计划",
            "task_breakdown": task_breakdown,
        })


def _sse(data: Dict[str, Any]) -> str:
    """格式化为 SSE 消息"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
