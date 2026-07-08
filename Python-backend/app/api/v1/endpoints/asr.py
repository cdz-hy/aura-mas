"""
语音识别端点 - 调用 MiMo-V2.5-ASR API 将用户语音转为文本
支持流式返回（SSE），识别结果逐 chunk 推送到前端输入框
"""
import json
import logging
import requests
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("api.asr")
router = APIRouter()


class TranscribeRequest(BaseModel):
    audio: str          # base64 编码的音频数据（不含 data URL 前缀）
    format: str = "wav" # 音频格式：wav、mp3 或 ogg
    language: str = "zh"  # 语种：zh、en、auto


@router.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    """
    接收前端录音的 base64 音频，调用 MiMo-V2.5-ASR 流式识别，
    以 SSE 格式逐 chunk 返回识别文本。
    """
    import asyncio
    import concurrent.futures

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    _SENTINEL = object()

    mime_map = {"wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg"}
    mime = mime_map.get(req.format, "audio/wav")
    data_url = f"data:{mime};base64,{req.audio}"

    def _call_asr():
        """在线程池中同步调用 MiMo ASR API（流式）"""
        try:
            url = f"{settings.MIMO_BASE_URL.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.MIMO_API_KEY}",
            }
            payload = {
                "model": "mimo-v2.5-asr",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {"data": data_url},
                            }
                        ],
                    }
                ],
                "asr_options": {"language": req.language},
                "stream": True,
            }

            logger.info(f"[ASR] 调用 MiMo ASR, format={req.format}, language={req.language}")
            resp = requests.post(url, headers=headers, json=payload, timeout=60, stream=True)

            if resp.status_code != 200:
                error_msg = f"ASR API 返回 {resp.status_code}: {resp.text[:200]}"
                logger.error(f"[ASR] {error_msg}")
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "text": error_msg}), loop
                )
                return

            # 流式过滤思考标签的缓冲区
            tag_buffer = ""
            in_think = False

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace")
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        # 用 buffer 处理跨 chunk 的 think 标签
                        tag_buffer += content
                        # 如果整个 buffer 都在 think 标签内，跳过
                        while tag_buffer:
                            if in_think:
                                end_idx = tag_buffer.find("</think>")
                                if end_idx == -1:
                                    # 还在 think 内，等更多数据
                                    tag_buffer = ""
                                    break
                                tag_buffer = tag_buffer[end_idx + 8:]
                                in_think = False
                            else:
                                start_idx = tag_buffer.find("<think>")
                                if start_idx == -1:
                                    # 没有 think 标签，输出全部
                                    asyncio.run_coroutine_threadsafe(
                                        queue.put({"type": "chunk", "text": tag_buffer}), loop
                                    )
                                    tag_buffer = ""
                                    break
                                # 输出 think 之前的部分
                                if start_idx > 0:
                                    asyncio.run_coroutine_threadsafe(
                                        queue.put({"type": "chunk", "text": tag_buffer[:start_idx]}), loop
                                    )
                                tag_buffer = tag_buffer[start_idx:]
                                in_think = True
                except json.JSONDecodeError:
                    continue

            logger.info("[ASR] 识别完成")

        except Exception as e:
            logger.error(f"[ASR] 调用失败: {e}", exc_info=True)
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "error", "text": str(e)}), loop
            )
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(_SENTINEL), loop)

    # 在线程池中启动 ASR 调用
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    executor.submit(_call_asr)

    async def _sse_generator():
        while True:
            item = await queue.get()
            if item is _SENTINEL:
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
