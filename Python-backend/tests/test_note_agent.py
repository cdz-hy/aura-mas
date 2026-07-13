"""Unit tests for note format request context handling."""
from app.api.v1.endpoints.note_agent import FormatRequest


def test_format_request_accepts_legacy_payload():
    req = FormatRequest(ticket="t", content="笔记正文")
    assert req.ticket == "t"
    assert req.content == "笔记正文"
    assert req.instruction == ""
    assert req.excerpt == ""
    assert req.source_title == ""
    assert req.note_type == ""


def test_format_request_accepts_camel_case_capture_context():
    req = FormatRequest(
        ticket="t",
        content="我的理解",
        instruction="更简洁",
        excerpt="当 x 趋近于 a 时",
        sourceTitle="极限的定义",
        noteType="excerpt",
    )
    assert req.excerpt == "当 x 趋近于 a 时"
    assert req.source_title == "极限的定义"
    assert req.note_type == "excerpt"
    assert req.instruction == "更简洁"


def test_format_request_accepts_snake_case_fields():
    req = FormatRequest(
        ticket="t",
        content="c",
        source_title="来源",
        note_type="question",
        excerpt="摘录",
    )
    assert req.source_title == "来源"
    assert req.note_type == "question"
    assert req.excerpt == "摘录"


def _build_user_prompt_from_request(req: FormatRequest) -> str:
    """Mirror the context assembly used in format_note for unit testing."""
    user_prompt = (
        "请整理以下笔记。注意：输出中必须包含 <<A:编号|类型|文本>> 批注标记，至少2处。\n\n"
    )
    if req.instruction.strip():
        user_prompt += f"用户特别要求：{req.instruction.strip()}\n\n"

    context_parts = []
    if req.source_title and req.source_title.strip():
        context_parts.append(f"学习来源：{req.source_title.strip()}")
    if req.note_type and req.note_type.strip():
        context_parts.append(f"笔记类型：{req.note_type.strip()}")
    if req.excerpt and req.excerpt.strip():
        context_parts.append(
            "摘录原文（来源材料，仅供参考，整理时不要覆盖或替换为摘录本身；"
            "请基于摘录理解并整理用户自己的思考内容）：\n"
            f"{req.excerpt.strip()}"
        )
    if context_parts:
        user_prompt += "\n".join(context_parts) + "\n\n"

    user_prompt += "用户笔记内容（需要整理的主体）：\n" + req.content
    return user_prompt


def test_user_prompt_includes_excerpt_as_source_material_not_body():
    req = FormatRequest(
        ticket="t",
        content="这是我对极限的理解",
        excerpt="当 x 趋近于 a 时",
        sourceTitle="极限的定义",
        noteType="excerpt",
    )
    prompt = _build_user_prompt_from_request(req)
    assert "当 x 趋近于 a 时" in prompt
    assert "不要覆盖" in prompt or "来源材料" in prompt
    assert "这是我对极限的理解" in prompt
    assert prompt.index("当 x 趋近于 a 时") < prompt.index("这是我对极限的理解")
    assert "学习来源：极限的定义" in prompt
    assert "笔记类型：excerpt" in prompt
