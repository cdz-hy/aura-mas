"""
全局 Session 流式回调注册表

LangGraph 使用 MemorySaver 时，即使是内存模式，也会通过 serde 序列化/反序列化状态，
这会导致 callable (函数) 值被过滤器剥离，无法通过 state 传递回调函数。

该注册表绕过 state 持久化问题，直接在内存中存储每个 session 的回调和占位资源映射，
节点通过 session_id 查询此注册表来获取回调。
"""
import threading
from typing import Callable, Dict, Any, Optional

_registry: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def register_session(
    session_id: str,
    sse_callback: Callable,
    create_placeholder_callback: Optional[Callable] = None,
    placeholder_resource_map: Optional[Dict] = None,
):
    """注册 session 的流式回调"""
    with _lock:
        _registry[session_id] = {
            "sse_callback": sse_callback,
            "create_placeholder_callback": create_placeholder_callback,
            "placeholder_resource_map": placeholder_resource_map or {},
        }


def update_placeholder_map(session_id: str, placeholder_map: Dict):
    """更新 session 的占位资源映射"""
    with _lock:
        if session_id in _registry:
            _registry[session_id]["placeholder_resource_map"] = placeholder_map


def get_sse_callback(session_id: str) -> Optional[Callable]:
    """获取 session 的 SSE 回调函数"""
    with _lock:
        entry = _registry.get(session_id)
        return entry["sse_callback"] if entry else None


def get_create_placeholder_callback(session_id: str) -> Optional[Callable]:
    """获取 session 的占位资源创建回调函数"""
    with _lock:
        entry = _registry.get(session_id)
        return entry.get("create_placeholder_callback") if entry else None


def get_placeholder_map(session_id: str) -> Dict:
    """获取 session 的占位资源映射"""
    with _lock:
        entry = _registry.get(session_id)
        return dict(entry["placeholder_resource_map"]) if entry else {}


def unregister_session(session_id: str):
    """注销 session 的流式回调（图执行完毕后调用）"""
    with _lock:
        _registry.pop(session_id, None)
