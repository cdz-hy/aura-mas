"""
闪卡生成 API - 从笔记内容中提取知识点生成 Q&A 闪卡
支持全篇生成和选中文字生成两种模式
SSE 流式输出生成进度
"""
import json
import asyncio
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.db.java_client import java_client
from app.agents.llm_factory import get_quiz_generator_llm
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("api.flashcard")
router = APIRouter()

FLASHCARD_PROMPT = """你是一位专业的学习助手。请从以下内容中提取关键知识点，生成 5-10 张闪卡。

每张闪卡包含：
- question：针对知识点的问题（正面）
- answer：简洁准确的答案（背面）
- difficulty：难度 1-简单 2-中等 3-困难

要求：
1. 覆盖核心概念、原理、公式、定义
2. 问题要具体明确，不要过于宽泛
3. 答案要精炼，不超过 100 字
4. 难度分布：至少 1 张简单、至少 1 张中等

严格输出 JSON 格式：
{
  "flashcards": [
    {"question": "...", "answer": "...", "difficulty": 1}
  ]
}"""

FLASHCARD_SELECTION_PROMPT = """你是一位专业的学习助手。用户从笔记中选中了一段文字，请根据这段选中内容生成 3-5 张闪卡。

每张闪卡包含：
- question：针对选中内容中知识点的问题（正面）
- answer：简洁准确的答案（背面）
- difficulty：难度 1-简单 2-中等 3-困难

要求：
1. 只围绕选中内容生成，不要扩展到其他内容
2. 问题要具体明确
3. 答案要精炼，不超过 100 字

严格输出 JSON 格式：
{
  "flashcards": [
    {"question": "...", "answer": "...", "difficulty": 1}
  ]
}"""


@router.get("/flashcard/generate")
async def generate_flashcards(
    ticket: str = Query(...),
    note_id: int = Query(..., gt=0),
    selected_text: Optional[str] = Query(None),
):
    """从笔记内容生成闪卡，SSE 流式返回

    selected_text: 如果提供，则只从选中文字生成闪卡
    """
    user_info = java_client.validate_ticket(ticket)
    user_id = user_info["user_id"]

    # 获取笔记内容
    try:
        note = java_client._request("GET", f"/api/note/internal/{note_id}")
    except Exception as e:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': f'获取笔记失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    note_content = note.get("content", "") if isinstance(note, dict) else ""
    note_name = note.get("noteName", "") if isinstance(note, dict) else ""
    note_owner = note.get("userId") if isinstance(note, dict) else None

    # 校验笔记所有权
    if note_owner and int(note_owner) != user_id:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': '无权操作该笔记'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # 确定生成模式
    is_selection_mode = bool(selected_text and selected_text.strip())
    source_text = selected_text.strip() if is_selection_mode else note_content

    if not source_text.strip():
        async def error_stream():
            msg = '选中内容为空' if is_selection_mode else '笔记内容为空'
            yield f"data: {json.dumps({'type': 'error', 'content': msg}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_stream() -> AsyncGenerator[str, None]:
        mode_desc = '选中内容' if is_selection_mode else '笔记内容'
        yield f"data: {json.dumps({'type': 'progress', 'content': f'正在分析{mode_desc}...'}, ensure_ascii=False)}\n\n"

        llm = get_quiz_generator_llm()

        if is_selection_mode:
            prompt = FLASHCARD_SELECTION_PROMPT
            user_msg = f"笔记标题：{note_name}\n\n选中的内容：\n{source_text[:3000]}"
        else:
            prompt = FLASHCARD_PROMPT
            user_msg = f"笔记标题：{note_name}\n\n笔记内容：\n{source_text[:6000]}"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg},
        ]

        try:
            result = await asyncio.to_thread(llm.chat_json, messages, 2048)
            record_from_mimo(llm, user_id, "flashcard_generation")
            flashcards = result.get("flashcards", [])

            if not flashcards:
                yield f"data: {json.dumps({'type': 'error', 'content': '未能生成闪卡，请检查内容'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'progress', 'content': f'已生成 {len(flashcards)} 张闪卡，正在保存...'}, ensure_ascii=False)}\n\n"

            # 全篇模式下先删除旧卡片防止重复（选中模式不删，因为是增量添加）
            if not is_selection_mode:
                try:
                    java_client._request("DELETE", f"/api/flashcard/internal/by-note/{note_id}",
                                         params={"userId": user_id})
                except Exception:
                    pass

            try:
                java_client._request("POST", "/api/flashcard/internal/save", json={
                    "userId": user_id,
                    "noteId": note_id,
                    "cards": flashcards,
                })
            except Exception as e:
                logger.error("保存闪卡失败: %s", e)
                yield f"data: {json.dumps({'type': 'error', 'content': f'保存闪卡失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                return

            # 逐张推送闪卡给前端展示
            for i, card in enumerate(flashcards):
                yield f"data: {json.dumps({'type': 'flashcard', 'index': i, 'total': len(flashcards), 'question': card.get('question', ''), 'answer': card.get('answer', ''), 'difficulty': card.get('difficulty', 1)}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'content': f'成功生成 {len(flashcards)} 张闪卡'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("闪卡生成失败: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'闪卡生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
