"""动画 Skill 生成节点单元测试：LLM 直出 HTML 架构。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agents.animation_skill_generator import (
    animation_skill_generator_node,
    _assemble_system_prompt,
    _assemble_user_message,
    _extract_html_from_response,
    _validate_js_syntax,
)


class FakeStreamLLM:
    def __init__(self, chunks):
        self.chunks = chunks
        self.request_timeout = None
        self.usage_records = []

    def chat_stream(self, messages, max_tokens=None):
        self.messages = messages
        self.max_tokens = max_tokens
        yield from self.chunks

    def get_usage_records(self):
        return self.usage_records


def make_skill():
    return SimpleNamespace(
        skill_md="# 测试 Skill",
        styles={"apple-tech-gradient": "风格规则"},
        templates={"apple-tech-gradient": "<style>:root{--bg:#000}.chip{color:red}</style>"},
        references={"script-audit": "审稿标准", "quality-check": "检查清单"},
    )


def make_state(**overrides):
    state = {
        "source_resource_content": "冒泡排序会反复比较相邻元素，并把较大的元素向后交换。",
        "user_profile": {},
        "task_breakdown": {"modules": [{"title": "排序算法", "description": "理解比较与交换"}]},
        "user_id": 1,
        "task_id": 100,
    }
    state.update(overrides)
    return state


def test_extract_html_from_markdown_code_block():
    response = "说明文字\n```html\n<!doctype html><html><body>动画</body></html>\n```\n"
    assert _extract_html_from_response(response) == "<!doctype html><html><body>动画</body></html>"


def test_validate_js_syntax_rejects_broken_script():
    html = "<html><body><script>function () {</script></body></html>"

    with patch("app.agents.animation_skill_generator.NODE_BIN", "node"), \
            patch("app.agents.animation_skill_generator.subprocess.run") as mock_run:
        mock_run.return_value = SimpleNamespace(
            returncode=1,
            stderr="temp.js:1\nSyntaxError: Function statements require a function name",
        )
        ok, error = _validate_js_syntax(html)

    assert ok is False
    assert "SyntaxError" in error
    mock_run.assert_called_once()


def test_validate_js_syntax_skips_when_node_is_unavailable():
    html = "<html><body><script>function () {</script></body></html>"

    with patch("app.agents.animation_skill_generator.NODE_BIN", None), \
            patch("app.agents.animation_skill_generator.subprocess.run") as mock_run:
        ok, error = _validate_js_syntax(html)

    assert ok is True
    assert error == ""
    mock_run.assert_not_called()


def test_validate_js_syntax_skips_non_javascript_script_types():
    html = """<html><body>
<script type="application/json">{"broken":}</script>
<script type="importmap">{"imports":{"lib":"./lib.js"}}</script>
<script>const ready = true;</script>
</body></html>"""
    checked = {}

    def fake_run(args, capture_output, text, timeout):
        with open(args[-1], encoding="utf-8") as script_file:
            checked["source"] = script_file.read()
        return SimpleNamespace(returncode=0, stderr="")

    with patch("app.agents.animation_skill_generator.NODE_BIN", "node"), \
            patch("app.agents.animation_skill_generator.subprocess.run", side_effect=fake_run) as mock_run:
        ok, error = _validate_js_syntax(html)

    assert ok is True
    assert error == ""
    mock_run.assert_called_once()
    assert "const ready = true;" in checked["source"]
    assert '"broken":' not in checked["source"]
    assert "imports" not in checked["source"]


def test_assemble_system_prompt_contains_current_direct_html_contract():
    prompt = _assemble_system_prompt(
        skill_md="SKILL内容",
        style_rules="风格规则",
        css_dna="<style>.chip{color:red}</style>",
        script_audit="审稿标准",
        quality_check="检查清单",
    )
    assert "全自动模式" in prompt
    assert "直接输出完整单文件 HTML" in prompt
    assert "GSAP 3 via CDN" in prompt
    assert "JavaScript 语法硬性要求" in prompt


def test_assemble_user_message_reads_current_profile_shape():
    profile = {"learning_behavior": {"visual_vs_verbal": -0.6, "sequential_vs_global": 0.7}}
    message = _assemble_user_message("标题", "正文", profile, "newspaper-evidence")
    assert "视觉型" in message
    assert "全局型" in message
    assert "newspaper-evidence" in message


@patch("app.agents.animation_skill_generator.load_skill", return_value=make_skill())
@patch("app.agents.animation_skill_generator.record_from_mimo")
def test_successful_direct_html_generation(mock_record, mock_load):
    html = """<!doctype html>
<html>
<head><script>const ready = true;</script></head>
<body><main id="stage"><section class="beat active">排序动画</section></main></body>
</html>"""
    llm = FakeStreamLLM([html])
    with patch("app.agents.animation_skill_generator.get_resource_type_generator_llm", return_value=llm):
        result = animation_skill_generator_node(make_state())

    generated = result["generated_content"]
    assert generated["module_type"] == "animation"
    assert generated["html"].startswith("<!doctype html>")
    assert generated["content"] == generated["html"]
    assert generated["metadata"]["renderer"] == "jacky-motion"
    assert generated["metadata"]["fallback"] is False
    assert llm.request_timeout == 300
    mock_load.assert_called_once_with("jacky-motion-main")


@patch("app.agents.animation_skill_generator.load_skill", return_value=make_skill())
@patch("app.agents.animation_skill_generator.record_from_mimo")
def test_broken_js_retries_then_uses_fallback(mock_record, mock_load):
    bad_html = "<!doctype html><html><body><script>function () {</script></body></html>"
    first_llm = FakeStreamLLM([bad_html])
    second_llm = FakeStreamLLM([bad_html])

    with patch("app.agents.animation_skill_generator.get_resource_type_generator_llm", side_effect=[first_llm, second_llm]):
        result = animation_skill_generator_node(make_state())

    generated = result["generated_content"]
    assert generated["metadata"]["fallback"] is True
    assert "排序算法" in generated["html"]
    assert generated["html"].startswith("<!doctype html>")


@patch("app.agents.animation_skill_generator.load_skill", return_value=make_skill())
@patch("app.agents.animation_skill_generator.record_from_mimo")
def test_empty_source_content_uses_title_and_description_fallback(mock_record, mock_load):
    raise_error_llm = MagicMock()
    raise_error_llm.chat_stream.side_effect = RuntimeError("LLM timeout")

    with patch("app.agents.animation_skill_generator.get_resource_type_generator_llm", return_value=raise_error_llm):
        result = animation_skill_generator_node(make_state(source_resource_content=""))

    generated = result["generated_content"]
    assert generated["metadata"]["fallback"] is True
    assert "排序算法" in generated["html"]
    assert "理解比较与交换" in generated["html"]
