"""
SSE 事件类型 - 与前端 Vue sse.ts 中的事件类型完全对应
前端期望的事件: progress, chunk, profile_update, question, profile_complete,
               modules, plan, resource, resource_trigger, recommendations,
               format_chunk, result_done, need_confirmation, done, error
"""
import json
from typing import Optional, Dict, Any, List


def sse_event(event_type: str, data: Any = None, **kwargs) -> str:
    """构造 SSE 消息 - data 字段为 JSON 对象"""
    payload = {"type": event_type}
    if data is not None:
        if isinstance(data, dict):
            payload.update(data)
        else:
            payload["data"] = data
    if kwargs:
        payload.update(kwargs)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def progress_event(content: str) -> str:
    """进度日志"""
    return sse_event("progress", content=content)


def chunk_event(content: str) -> str:
    """文本增量（LLM 流式输出）"""
    return sse_event("chunk", content=content)


def format_chunk_event(content: str) -> str:
    """格式化文本增量"""
    return sse_event("format_chunk", content=content)


def profile_update_event(dimensions: Dict[str, Any]) -> str:
    """画像维度更新"""
    return sse_event("profile_update", dimensions=dimensions)


def profile_complete_event(profile: Dict[str, Any]) -> str:
    """画像构建完成"""
    return sse_event("profile_complete", profile=profile)


def question_event(question: str) -> str:
    """向用户提问"""
    return sse_event("question", question=question)


def modules_event(modules: List[Dict[str, Any]]) -> str:
    """模块列表"""
    return sse_event("modules", data=modules)


def plan_event(plan: Dict[str, Any]) -> str:
    """完整计划数据"""
    return sse_event("plan", data=plan)


def resource_event(resource: Dict[str, Any]) -> str:
    """生成的学习资源"""
    return sse_event("resource", data=resource)


def resource_trigger_event(resource_type: str, module_id: int) -> str:
    """触发资源生成"""
    return sse_event("resource_trigger", resource_type=resource_type, module_id=module_id)


def recommendations_event(data: List[Dict[str, Any]]) -> str:
    """推荐内容"""
    return sse_event("recommendations", data=data)


def done_event() -> str:
    """完成"""
    return sse_event("done")


def result_done_event() -> str:
    """结果完成（别名）"""
    return sse_event("result_done")


def error_event(content: str) -> str:
    """错误"""
    return sse_event("error", content=content)


def need_confirmation_event(message: str, task_breakdown: Any = None) -> str:
    """需要用户确认"""
    data = {"message": message}
    if task_breakdown:
        data["task_breakdown"] = task_breakdown
    return sse_event("need_confirmation", **data)
