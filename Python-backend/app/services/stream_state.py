"""
流式状态缓存 - 用于刷新后恢复流式输出动画和停止信号
内存级缓存，按 session_id 存储当前流式文本和状态
"""
import threading
import time
import logging

logger = logging.getLogger("stream_state")

# 内存缓存：session_id -> {text, is_streaming, last_update, source}
_cache: dict[str, dict] = {}
_lock = threading.Lock()

# 停止信号集合：用户主动停止的 session_id
_stop_signals: set[str] = set()
_stop_lock = threading.Lock()

# 缓存过期时间（秒）：流式结束后保留一段时间供客户端恢复
EXPIRE_SECONDS = 300  # 5 分钟


def update_stream_text(session_id: str, text: str, source: str = "chat"):
    """追加流式文本（每次 chunk 调用）"""
    with _lock:
        if session_id not in _cache:
            _cache[session_id] = {
                "text": "",
                "is_streaming": True,
                "last_update": time.time(),
                "source": source,
            }
        _cache[session_id]["text"] = text
        _cache[session_id]["last_update"] = time.time()


def mark_stream_done(session_id: str):
    """标记流式完成"""
    with _lock:
        if session_id in _cache:
            _cache[session_id]["is_streaming"] = False
            _cache[session_id]["last_update"] = time.time()
            logger.info(f"[流式缓存] 会话 {session_id} 流式完成, 文本长度: {len(_cache[session_id]['text'])}")


def mark_stream_error(session_id: str, error: str):
    """标记流式异常"""
    with _lock:
        if session_id in _cache:
            _cache[session_id]["is_streaming"] = False
            _cache[session_id]["error"] = error
            _cache[session_id]["last_update"] = time.time()


def get_stream_state(session_id: str) -> dict | None:
    """获取流式状态（供前端轮询）"""
    with _lock:
        state = _cache.get(session_id)
        if not state:
            return None
        # 检查是否过期
        if time.time() - state["last_update"] > EXPIRE_SECONDS:
            del _cache[session_id]
            return None
        return {
            "text": state["text"],
            "is_streaming": state["is_streaming"],
            "source": state.get("source", "chat"),
            "error": state.get("error"),
        }


# ─── 停止信号管理 ───

def request_stop(session_id: str):
    """请求停止指定会话的流式处理"""
    with _stop_lock:
        _stop_signals.add(session_id)
        logger.info(f"[停止信号] 会话 {session_id} 请求停止")


def check_stop(session_id: str) -> bool:
    """检查会话是否被请求停止（供后台线程调用）"""
    with _stop_lock:
        return session_id in _stop_signals


def clear_stop(session_id: str):
    """清除停止信号（处理完成后调用）"""
    with _stop_lock:
        _stop_signals.discard(session_id)


def cleanup_expired():
    """清理过期缓存（可由定时任务调用）"""
    now = time.time()
    with _lock:
        expired = [sid for sid, s in _cache.items() if now - s["last_update"] > EXPIRE_SECONDS]
        for sid in expired:
            del _cache[sid]
    if expired:
        logger.info(f"[流式缓存] 清理 {len(expired)} 个过期条目")
