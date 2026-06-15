"""动画 Skill 生成节点单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from app.agents.animation_skill_generator import (
    animation_skill_generator_node,
    _assemble_system_prompt,
    _assemble_user_message,
    _render_animation_html,
)


class TestAssembleSystemPrompt:
    """测试 system prompt 组装"""

    def test_contains_all_parts(self):
        prompt = _assemble_system_prompt("SKILL内容", "CSS内容", "检查清单")
        assert "SKILL内容" in prompt
        assert "CSS内容" in prompt
        assert "检查清单" in prompt

    def test_empty_css_dna(self):
        prompt = _assemble_system_prompt("SKILL内容", "", "检查清单")
        assert "SKILL内容" in prompt
        assert "检查清单" in prompt
        assert "CSS DNA" not in prompt

    def test_empty_quality_check(self):
        prompt = _assemble_system_prompt("SKILL内容", "CSS内容", "")
        assert "SKILL内容" in prompt
        assert "CSS内容" in prompt
        assert "自检清单" not in prompt


class TestAssembleUserMessage:
    """测试 user message 组装"""

    def test_includes_source_info(self):
        msg = _assemble_user_message("测试标题", "测试内容", {}, 60)
        assert "测试标题" in msg
        assert "测试内容" in msg

    def test_truncates_long_content(self):
        long_content = "x" * 10000
        msg = _assemble_user_message("标题", long_content, {}, 60)
        assert "已截断" in msg
        assert len(msg) < len(long_content) + 500

    def test_user_profile_preferences(self):
        profile = {
            "learning_behavior": {
                "felder_silverman": {
                    "visual_verbal": -0.6,
                    "sequential_global": 0.5,
                }
            }
        }
        msg = _assemble_user_message("标题", "内容", profile, 60)
        assert "视觉型" in msg
        assert "全局型" in msg


class TestAnimationSkillGeneratorNode:
    """测试动画生成节点"""

    def _make_state(self, **overrides):
        base = {
            "source_resource_content": "这是测试源资源内容",
            "user_profile": {},
            "task_breakdown": {"modules": [{"title": "测试模块", "description": "测试描述"}]},
            "user_id": 1,
            "task_id": 100,
        }
        base.update(overrides)
        return base

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_empty_source_content_still_generates_animation(self, mock_record, mock_llm_factory, mock_load):
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试"
        mock_skill.templates = {"apple-tech-gradient": ""}
        mock_skill.references = {"quality-check": ""}
        mock_load.return_value = mock_skill

        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "title": "测试模块 - 动画演示",
            "animationSpec": {"beats": [{"screenText": "最小上下文", "coreIdea": "从标题生成动画"}]},
        }
        mock_llm_factory.return_value = mock_llm

        state = self._make_state(source_resource_content="")
        result = animation_skill_generator_node(state)

        assert "error" not in result
        assert result["generated_content"]["module_type"] == "animation"
        assert "最小上下文" in result["generated_content"]["html"]

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_empty_source_content_uses_title_fallback(self, mock_record, mock_llm_factory, mock_load):
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试"
        mock_skill.templates = {"apple-tech-gradient": ""}
        mock_skill.references = {"quality-check": ""}
        mock_load.return_value = mock_skill

        mock_llm = MagicMock()
        mock_llm.chat_json.side_effect = Exception("MIMO API 请求超时（45秒）")
        mock_llm_factory.return_value = mock_llm

        state = self._make_state(source_resource_content="")
        result = animation_skill_generator_node(state)

        assert "error" not in result
        assert result["generated_content"]["module_type"] == "animation"
        assert "测试模块" in result["generated_content"]["html"]
        assert result["generated_content"]["metadata"]["fallback"] is True

    @patch("app.agents.animation_skill_generator.load_skill")
    def test_skill_load_failure_returns_error(self, mock_load):
        mock_load.side_effect = FileNotFoundError("test error")
        state = self._make_state()
        result = animation_skill_generator_node(state)
        assert "error" in result
        assert "skill" in result["error"].lower()

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_successful_generation(self, mock_record, mock_llm_factory, mock_load):
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试 Skill"
        mock_skill.templates = {"apple-tech-gradient": "CSS内容"}
        mock_skill.references = {"quality-check": "检查清单"}
        mock_load.return_value = mock_skill

        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "title": "测试 - 动画演示",
            "description": "测试描述",
            "html": "<!doctype html><html><body>test</body></html>",
            "content": "<!doctype html><html><body>test</body></html>",
            "animationSpec": {"style": "apple-tech-gradient", "beats": []},
            "duration": 60,
            "metadata": {"renderer": "aura-teaching-animation"},
        }
        mock_llm_factory.return_value = mock_llm

        state = self._make_state()
        result = animation_skill_generator_node(state)

        assert "error" not in result
        assert result["generated_content"]["module_type"] == "animation"
        assert result["generated_content"]["html"] != "<!doctype html><html><body>test</body></html>"
        assert "animation-control-bar" in result["generated_content"]["html"]
        assert "data-action=\"pause\"" in result["generated_content"]["html"]
        assert "startAutoplay" in result["generated_content"]["html"]
        assert "aspect-ratio:16/9" in result["generated_content"]["html"]
        assert "width:min(100vw,calc(100vh * 16 / 9))" in result["generated_content"]["html"]
        assert result["generated_content"]["content"] == result["generated_content"]["html"]
        mock_load.assert_called_once_with("motion")
        assert mock_llm.request_timeout == 45

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_spec_only_result_renders_html_locally(self, mock_record, mock_llm_factory, mock_load):
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试"
        mock_skill.templates = {"apple-tech-gradient": ""}
        mock_skill.references = {"quality-check": ""}
        mock_load.return_value = mock_skill

        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "title": "测试 - 动画演示",
            "description": "本地渲染 HTML",
            "animationSpec": {
                "beats": [{
                    "id": "b1",
                    "coreIdea": "用动画展示核心概念。",
                    "screenText": "核心概念",
                    "steps": ["输入", "处理", "输出"],
                }],
            },
        }
        mock_llm_factory.return_value = mock_llm

        state = self._make_state()
        result = animation_skill_generator_node(state)
        assert "error" not in result
        html = result["generated_content"]["html"]
        assert html.startswith("<!doctype html>")
        assert "核心概念" in html
        assert "AURA_ANIMATION_READY" in html
        assert "animation-control-bar" in html
        assert "data-action=\"pause\"" in html
        mock_llm.chat_json.assert_called_once()
        assert mock_llm.chat_json.call_args.kwargs["max_tokens"] <= 4096

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_llm_timeout_uses_local_fallback_animation(self, mock_record, mock_llm_factory, mock_load):
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试"
        mock_skill.templates = {"apple-tech-gradient": ""}
        mock_skill.references = {"quality-check": ""}
        mock_load.return_value = mock_skill

        mock_llm = MagicMock()
        mock_llm.chat_json.side_effect = Exception("MIMO API 请求超时（120秒）")
        mock_llm_factory.return_value = mock_llm

        state = self._make_state(source_resource_content="第一段说明。\n\n第二段说明。\n\n第三段说明。")
        result = animation_skill_generator_node(state)

        assert "error" not in result
        assert result["generated_content"]["metadata"]["fallback"] is True
        assert result["generated_content"]["html"].startswith("<!doctype html>")
        mock_record.assert_not_called()


def test_render_animation_html_escapes_untrusted_text():
    html = _render_animation_html(
        title="<script>alert(1)</script>",
        description="desc",
        animation_spec={
            "beats": [{
                "screenText": "<img src=x onerror=alert(1)>",
                "coreIdea": "核心 <b>文本</b>",
                "steps": ["步骤 <script>bad()</script>"],
            }],
        },
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "步骤 &lt;script&gt;bad()&lt;/script&gt;" in html


def test_render_animation_html_is_responsive_and_has_playback_controls():
    html = _render_animation_html(
        title="响应式动画",
        description="desc",
        animation_spec={
            "beats": [{
                "screenText": "第一屏",
                "coreIdea": "测试完整显示",
                "steps": ["步骤一"],
            }, {
                "screenText": "第二屏",
                "coreIdea": "测试前进后退",
                "steps": ["步骤二"],
            }],
        },
    )

    assert "width:100vw" in html
    assert "height:100vh" in html
    assert "animation-control-bar" in html
    assert "data-action=\"prev\"" in html
    assert "data-action=\"pause\"" in html
    assert "data-action=\"replay\"" in html
    assert "data-action=\"next\"" in html
    assert "startAutoplay" in html
