# Animation Skill Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the `jacky-motion-main` animation skill into the AURA LangGraph pipeline so that `type=animation` requests produce self-contained HTML animations via a new dedicated node.

**Architecture:** A generic skill loader reads files from `skills/<name>/` directories. A new `animation_skill_generator` node uses the loader to read SKILL.md, style templates (CSS DNA), and quality checklist, assembles a prompt, calls the LLM, and returns `generated_content` with `html`/`animationSpec`/`metadata`. The node is wired into the existing LangGraph as a terminal leaf node, routed via `resource_chat.py` when `type=animation`.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, MIMO LLM (OpenAI-compatible)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `Python-backend/app/skills/__init__.py` | Package init |
| Create | `Python-backend/app/skills/loader.py` | Generic skill loader: reads SKILL.md, references/, styles/, assets/templates/ |
| Create | `Python-backend/tests/test_skill_loader.py` | Unit tests for skill loader |
| Create | `Python-backend/app/agents/animation_skill_generator.py` | Animation node: load skill, assemble prompt, call LLM, validate output |
| Create | `Python-backend/tests/test_animation_skill_generator.py` | Unit tests for animation node |
| Modify | `Python-backend/app/agents/schemas.py:21` | Add `NODE_ANIMATION_SKILL_GENERATOR` constant |
| Modify | `Python-backend/app/graph/learning_graph.py` | Import, register node, add route function, add edges, add to controller mapping |
| Modify | `Python-backend/app/api/v1/endpoints/resource_chat.py:22,632-646` | Add import, add `type=animation` routing branch |

---

### Task 1: Skill Loader

**Files:**
- Create: `Python-backend/app/skills/__init__.py`
- Create: `Python-backend/app/skills/loader.py`
- Create: `Python-backend/tests/test_skill_loader.py`

- [ ] **Step 1: Create the skills package init**

```python
# Python-backend/app/skills/__init__.py
```

Empty file, just marks the directory as a Python package.

- [ ] **Step 2: Write the skill loader module**

```python
# Python-backend/app/skills/loader.py
"""
通用 Skill Loader — 按约定目录结构从 skills/ 加载任意 skill 文件

约定结构:
    skills/<skill-name>/
    ├── SKILL.md              # 必须
    ├── references/           # 可选, *.md
    ├── styles/               # 可选, *.md
    └── assets/templates/     # 可选, *.html
"""
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("skills.loader")

# skills 目录位于 Python-backend/skills/
SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent / "skills"


@dataclass
class SkillBundle:
    """一个 skill 的全部文件内容"""
    name: str
    skill_md: str = ""                          # SKILL.md 原文
    references: dict[str, str] = field(default_factory=dict)  # {stem: content}
    styles: dict[str, str] = field(default_factory=dict)      # {stem: content}
    templates: dict[str, str] = field(default_factory=dict)   # {stem: content}


def _read_files_in_dir(dir_path: Path, suffix: str) -> dict[str, str]:
    """读取目录下指定后缀的文件，返回 {stem: content}"""
    result = {}
    if not dir_path.is_dir():
        return result
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix == suffix:
            try:
                result[f.stem] = f.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"读取文件失败 {f}: {e}")
    return result


def load_skill(skill_name: str) -> SkillBundle:
    """
    从 skills/<skill_name>/ 加载所有文件。

    Args:
        skill_name: skill 目录名，例如 "jacky-motion-main"

    Returns:
        SkillBundle 包含所有加载的文件内容

    Raises:
        FileNotFoundError: skill 目录不存在或缺少 SKILL.md
    """
    skill_dir = SKILLS_ROOT / skill_name

    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill 目录不存在: {skill_dir}")

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise FileNotFoundError(f"SKILL.md 不存在: {skill_md_path}")

    skill_md = skill_md_path.read_text(encoding="utf-8")

    references = _read_files_in_dir(skill_dir / "references", ".md")
    styles = _read_files_in_dir(skill_dir / "styles", ".md")
    templates = _read_files_in_dir(skill_dir / "assets" / "templates", ".html")

    bundle = SkillBundle(
        name=skill_name,
        skill_md=skill_md,
        references=references,
        styles=styles,
        templates=templates,
    )

    logger.info(
        f"已加载 skill '{skill_name}': "
        f"SKILL.md={len(skill_md)}字符, "
        f"references={len(references)}, "
        f"styles={len(styles)}, "
        f"templates={len(templates)}"
    )

    return bundle
```

- [ ] **Step 3: Write tests for the skill loader**

```python
# Python-backend/tests/test_skill_loader.py
"""Skill Loader 单元测试"""
import pytest
from pathlib import Path
from app.skills.loader import load_skill, SkillBundle, SKILLS_ROOT


class TestLoadSkill:
    """测试 load_skill 函数"""

    def test_load_jacky_motion_main(self):
        """加载真实的 jacky-motion-main skill"""
        bundle = load_skill("jacky-motion-main")

        assert isinstance(bundle, SkillBundle)
        assert bundle.name == "jacky-motion-main"

        # SKILL.md 必须存在且非空
        assert len(bundle.skill_md) > 0
        assert "Aura 教学动画导演" in bundle.skill_md

        # references 应包含 quality-check
        assert "quality-check" in bundle.references
        assert "验收检查" in bundle.references["quality-check"]

        # templates 应包含 4 个 style HTML
        assert len(bundle.templates) == 4
        assert "apple-tech-gradient" in bundle.templates
        assert "editorial-magazine" in bundle.templates
        assert "finance-studio-cards" in bundle.templates
        assert "newspaper-evidence" in bundle.templates

        # styles 应包含 4 个 style md
        assert len(bundle.styles) == 4

    def test_nonexistent_skill_raises(self):
        """不存在的 skill 目录应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Skill 目录不存在"):
            load_skill("nonexistent-skill")

    def test_skills_root_exists(self):
        """SKILLS_ROOT 指向的目录必须存在"""
        assert SKILLS_ROOT.is_dir()
```

- [ ] **Step 4: Run tests**

```bash
cd Python-backend && python -m pytest tests/test_skill_loader.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add Python-backend/app/skills/__init__.py Python-backend/app/skills/loader.py Python-backend/tests/test_skill_loader.py
git commit -m "feat: add generic skill loader for loading skills from directory structure"
```

---

### Task 2: Add Node Constant to schemas.py

**Files:**
- Modify: `Python-backend/app/agents/schemas.py:21`

- [ ] **Step 1: Add the constant**

In `Python-backend/app/agents/schemas.py`, after line 21 (`NODE_RESOURCE_TYPE_GENERATOR = "resource_type_generator"`), add:

```python
NODE_ANIMATION_SKILL_GENERATOR = "animation_skill_generator"
```

- [ ] **Step 2: Verify no import errors**

```bash
cd Python-backend && python -c "from app.agents.schemas import NODE_ANIMATION_SKILL_GENERATOR; print(NODE_ANIMATION_SKILL_GENERATOR)"
```

Expected: `animation_skill_generator`

- [ ] **Step 3: Commit**

```bash
git add Python-backend/app/agents/schemas.py
git commit -m "feat: add NODE_ANIMATION_SKILL_GENERATOR constant to schemas"
```

---

### Task 3: Animation Skill Generator Node

**Files:**
- Create: `Python-backend/app/agents/animation_skill_generator.py`
- Create: `Python-backend/tests/test_animation_skill_generator.py`

- [ ] **Step 1: Write the animation node**

```python
# Python-backend/app/agents/animation_skill_generator.py
"""
动画 Skill 生成智能体节点 — 读取本地 skill 文件，生成教学动画 HTML
"""
import logging
from typing import Dict, Any

from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_type_generator_llm
from app.skills.loader import load_skill
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("agents.animation_skill_generator")

DEFAULT_STYLE = "apple-tech-gradient"


def _assemble_system_prompt(skill_md: str, css_dna: str, quality_check: str) -> str:
    """组装动画生成的 system prompt"""
    parts = [skill_md]
    if css_dna:
        parts.append(f"\n\n## 当前风格 CSS DNA\n\n以下是你要使用的视觉风格的完整 CSS 变量和组件类。"
                      f"你必须基于这些 CSS DNA 来生成动画 HTML，不要自行发明颜色、字体或布局系统。\n\n{css_dna}")
    if quality_check:
        parts.append(f"\n\n## 交付前自检清单\n\n生成 HTML 后，逐条对照以下检查项。"
                      f"不通过的先修复，再输出 JSON。\n\n{quality_check}")
    return "\n".join(parts)


def _assemble_user_message(
    source_title: str,
    source_content: str,
    user_profile: dict,
    target_duration: int,
) -> str:
    """组装动画生成的 user message"""
    # 用户偏好
    behavior = user_profile.get("learning_behavior", {})
    fs = behavior.get("felder_silverman", {})
    vv = fs.get("visual_verbal", 0)
    sg = fs.get("sequential_global", 0)

    vv_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")
    sg_text = "序列型" if sg < -0.3 else ("全局型" if sg > 0.3 else "均衡型")

    # 截断源内容，避免超出上下文窗口
    max_content_len = 6000
    truncated = source_content[:max_content_len]
    if len(source_content) > max_content_len:
        truncated += f"\n\n... (源内容共 {len(source_content)} 字符，已截断)"

    return f"""请基于以下学习资源生成一个教学动画。

## 源资源标题
{source_title}

## 源资源正文
{truncated}

## 用户偏好
- 视觉/言语倾向: {vv_text} (值: {vv})
- 序列/全局倾向: {sg_text} (值: {sg})

## 要求
- 目标时长: {target_duration} 秒
- 从源资源中提炼一个最值得动画化的主线（流程 > 关系 > 对比 > 抽象概念）
- 生成 3-6 个 beat
- 输出严格 JSON，不要 Markdown 包裹

请输出 JSON:"""


def animation_skill_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    动画 Skill 生成节点

    1. 从 state 取源资源内容和用户画像
    2. 加载 jacky-motion-main skill 文件
    3. 组装 prompt（SKILL.md + CSS DNA + 质量检查）
    4. 调 LLM 生成 HTML + animationSpec
    5. 校验输出，返回 generated_content
    """
    source_resource_content = state.get("source_resource_content", "")
    user_profile = state.get("user_profile", {})
    task_breakdown = state.get("task_breakdown", {})

    # 从 task_breakdown 提取标题和描述
    modules = task_breakdown.get("modules", [])
    module_title = ""
    module_desc = ""
    if modules:
        module_title = modules[0].get("title", "")
        module_desc = modules[0].get("description", "")

    source_title = module_title or "未知资源"

    logger.info(f"{'='*60}")
    logger.info(f"  [动画生成] 开始处理")
    logger.info(f"  源资源标题: {source_title}")
    logger.info(f"  源资源内容长度: {len(source_resource_content)} 字符")

    if not source_resource_content:
        logger.warning("  [动画生成] 源资源内容为空，无法生成动画")
        return {
            "error": "源资源内容为空，无法生成动画",
            "current_step": "动画生成: 源资源内容为空",
            "stream_events": [{
                "event_type": "error",
                "agent": "animation_skill_generator",
                "data": {"error": "源资源内容为空"},
                "step_description": "动画生成失败: 源资源内容为空",
            }],
        }

    # 加载 skill 文件
    try:
        skill = load_skill("jacky-motion-main")
    except FileNotFoundError as e:
        logger.error(f"  [动画生成] 加载 skill 失败: {e}")
        return {
            "error": f"加载动画 skill 失败: {e}",
            "current_step": f"动画生成: skill 加载失败",
            "stream_events": [{
                "event_type": "error",
                "agent": "animation_skill_generator",
                "data": {"error": str(e)},
                "step_description": "动画生成失败: skill 文件缺失",
            }],
        }

    # 选择 style 模板
    css_dna = skill.templates.get(DEFAULT_STYLE, "")
    if not css_dna:
        logger.warning(f"  [动画生成] 默认风格 {DEFAULT_STYLE} 模板为空")

    # 组装 prompt
    quality_check = skill.references.get("quality-check", "")
    system_prompt = _assemble_system_prompt(skill.skill_md, css_dna, quality_check)
    user_message = _assemble_user_message(
        source_title=source_title,
        source_content=source_resource_content,
        user_profile=user_profile,
        target_duration=60,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # 调 LLM
    try:
        llm = get_resource_type_generator_llm()
        logger.info(f"  [动画生成] 正在调用 LLM...")
        result = llm.chat_json(messages, max_tokens=16384)
        record_from_mimo(llm, state.get("user_id", 0), "animation_generation", state.get("task_id"))
    except Exception as e:
        logger.error(f"  [动画生成] LLM 调用失败: {e}")
        return {
            "error": f"动画生成 LLM 调用失败: {e}",
            "current_step": f"动画生成: LLM 调用失败",
            "stream_events": [{
                "event_type": "error",
                "agent": "animation_skill_generator",
                "data": {"error": str(e)},
                "step_description": "动画生成失败: LLM 调用异常",
            }],
        }

    # 校验输出
    html = result.get("html", "")
    animation_spec = result.get("animationSpec")

    if not html:
        logger.error("  [动画生成] LLM 返回的 html 字段为空")
        return {
            "error": "动画生成失败: LLM 未返回 html 内容",
            "current_step": "动画生成: html 为空",
            "stream_events": [{
                "event_type": "error",
                "agent": "animation_skill_generator",
                "data": {"error": "html 字段为空"},
                "step_description": "动画生成失败: html 为空",
            }],
        }

    if not animation_spec:
        logger.warning("  [动画生成] LLM 未返回 animationSpec，将使用空对象")
        animation_spec = {}

    # 构造输出
    generated = {
        "module_type": "animation",
        "title": result.get("title", f"{source_title} - 动画演示"),
        "description": result.get("description", ""),
        "html": html,
        "content": html,  # 与 html 相同，兼容现有持久化逻辑
        "animationSpec": animation_spec,
        "duration": result.get("duration", 60),
        "metadata": result.get("metadata", {
            "renderer": "aura-teaching-animation",
            "version": "1.0",
            "source": "current_resource",
            "interactive": True,
        }),
    }

    logger.info(f"  [动画生成] 生成完成!")
    logger.info(f"    标题: {generated['title']}")
    logger.info(f"    HTML 长度: {len(html)} 字符")
    logger.info(f"    beats 数: {len(animation_spec.get('beats', []))}")
    logger.info(f"{'='*60}")

    return {
        "generated_content": generated,
        "current_step": f"动画生成: 已生成动画资源「{generated['title']}」",
        "stream_events": [{
            "event_type": "resource_type_generated",
            "agent": "animation_skill_generator",
            "data": generated,
            "step_description": f"已生成动画资源",
        }],
    }
```

- [ ] **Step 2: Write tests for the animation node**

```python
# Python-backend/tests/test_animation_skill_generator.py
"""动画 Skill 生成节点单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from app.agents.animation_skill_generator import (
    animation_skill_generator_node,
    _assemble_system_prompt,
    _assemble_user_message,
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
        # 不应包含 CSS DNA 注入段
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

    def test_empty_source_content_returns_error(self):
        """源资源内容为空时应返回错误"""
        state = self._make_state(source_resource_content="")
        result = animation_skill_generator_node(state)
        assert "error" in result
        assert "源资源内容为空" in result["error"]

    @patch("app.agents.animation_skill_generator.load_skill")
    def test_skill_load_failure_returns_error(self, mock_load):
        """skill 加载失败时应返回错误"""
        mock_load.side_effect = FileNotFoundError("test error")
        state = self._make_state()
        result = animation_skill_generator_node(state)
        assert "error" in result
        assert "skill" in result["error"].lower()

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_successful_generation(self, mock_record, mock_llm_factory, mock_load):
        """正常生成流程"""
        # mock skill loader
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试 Skill"
        mock_skill.templates = {"apple-tech-gradient": "CSS内容"}
        mock_skill.references = {"quality-check": "检查清单"}
        mock_load.return_value = mock_skill

        # mock LLM
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
        assert result["generated_content"]["html"] == "<!doctype html><html><body>test</body></html>"
        assert result["generated_content"]["content"] == result["generated_content"]["html"]

    @patch("app.agents.animation_skill_generator.load_skill")
    @patch("app.agents.animation_skill_generator.get_resource_type_generator_llm")
    @patch("app.agents.animation_skill_generator.record_from_mimo")
    def test_empty_html_returns_error(self, mock_record, mock_llm_factory, mock_load):
        """LLM 返回空 html 时应返回错误"""
        mock_skill = MagicMock()
        mock_skill.skill_md = "# 测试"
        mock_skill.templates = {"apple-tech-gradient": ""}
        mock_skill.references = {"quality-check": ""}
        mock_load.return_value = mock_skill

        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {"html": "", "animationSpec": {}}
        mock_llm_factory.return_value = mock_llm

        state = self._make_state()
        result = animation_skill_generator_node(state)
        assert "error" in result
        assert "html" in result["error"]
```

- [ ] **Step 3: Run tests**

```bash
cd Python-backend && python -m pytest tests/test_animation_skill_generator.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add Python-backend/app/agents/animation_skill_generator.py Python-backend/tests/test_animation_skill_generator.py
git commit -m "feat: add animation skill generator node with prompt assembly and output validation"
```

---

### Task 4: Wire Node into LangGraph

**Files:**
- Modify: `Python-backend/app/graph/learning_graph.py`

- [ ] **Step 1: Add import for the new node constant**

In `Python-backend/app/graph/learning_graph.py`, at line 13, add `NODE_ANIMATION_SKILL_GENERATOR` to the existing import:

```python
from app.agents.schemas import (
    AgentState,
    NODE_CONTROLLER, NODE_TASK_DECOMPOSER, NODE_SIMPLE_ANSWER,
    NODE_RAG_RETRIEVER, NODE_RESOURCE_GENERATOR, NODE_QUIZ_GENERATOR,
    NODE_QUIZ_GRADER, NODE_RESOURCE_TYPE_GENERATOR,
    NODE_ANIMATION_SKILL_GENERATOR,
    NODE_PROFILE_MAINTAINER, NODE_HUMAN_CONFIRM,
    NODE_REVIEW_ORCHESTRATE,
    INTENT_GENERATE_RESOURCE, INTENT_SIMPLE_QA, INTENT_GENERATE_QUIZ,
    INTENT_GRADE_QUIZ, INTENT_AMBIGUOUS, INTENT_FOLLOW_UP,
)
```

- [ ] **Step 2: Add import for the node function**

After line 27 (`from app.agents.resource_type_generator import resource_type_generator_node`), add:

```python
from app.agents.animation_skill_generator import animation_skill_generator_node
```

- [ ] **Step 3: Register the node in build_learning_graph()**

After line 533 (`graph.add_node(NODE_RESOURCE_TYPE_GENERATOR, resource_type_generator_node)`), add:

```python
graph.add_node(NODE_ANIMATION_SKILL_GENERATOR, animation_skill_generator_node)
```

Update the log message on line 536 from 10 to 11:

```python
logger.info("已注册 11 个节点")
```

- [ ] **Step 4: Add the route function**

After the `route_after_controller` function (after line 60), add:

```python
def route_after_animation_skill_generator(state: AgentState) -> str:
    """动画生成之后的路由"""
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly
    if state.get("error"):
        return NODE_CONTROLLER
    return END
```

- [ ] **Step 5: Add to controller mapping**

In the `route_after_controller` conditional edges mapping (lines 545-555), add one entry before `END`:

```python
{
    NODE_TASK_DECOMPOSER: NODE_TASK_DECOMPOSER,
    NODE_SIMPLE_ANSWER: NODE_SIMPLE_ANSWER,
    NODE_RAG_RETRIEVER: NODE_RAG_RETRIEVER,
    NODE_QUIZ_GENERATOR: NODE_QUIZ_GENERATOR,
    NODE_QUIZ_GRADER: NODE_QUIZ_GRADER,
    NODE_RESOURCE_GENERATOR: NODE_RESOURCE_GENERATOR,
    NODE_RESOURCE_TYPE_GENERATOR: NODE_RESOURCE_TYPE_GENERATOR,
    NODE_ANIMATION_SKILL_GENERATOR: NODE_ANIMATION_SKILL_GENERATOR,
    NODE_HUMAN_CONFIRM: NODE_HUMAN_CONFIRM,
    END: END,
}
```

- [ ] **Step 6: Add conditional edges for the new node**

After the `resource_type_generator` edges block (around line 640), add:

```python
# 动画生成 -> 结束或回主控
graph.add_conditional_edges(
    NODE_ANIMATION_SKILL_GENERATOR,
    route_after_animation_skill_generator,
    {
        NODE_CONTROLLER: NODE_CONTROLLER,
        END: END,
    }
)
```

- [ ] **Step 7: Verify graph builds without errors**

```bash
cd Python-backend && python -c "from app.graph.learning_graph import build_learning_graph; g = build_learning_graph(); print('Graph built successfully')"
```

Expected: `Graph built successfully`

- [ ] **Step 8: Commit**

```bash
git add Python-backend/app/graph/learning_graph.py
git commit -m "feat: wire animation_skill_generator node into LangGraph"
```

---

### Task 5: Add Routing in resource_chat.py

**Files:**
- Modify: `Python-backend/app/api/v1/endpoints/resource_chat.py:22,632-646`

- [ ] **Step 1: Add import**

At line 22, change:

```python
from app.agents.schemas import AgentState, NODE_RESOURCE_TYPE_GENERATOR
```

to:

```python
from app.agents.schemas import AgentState, NODE_RESOURCE_TYPE_GENERATOR, NODE_ANIMATION_SKILL_GENERATOR
```

- [ ] **Step 2: Add animation routing branch**

At lines 632-646, change:

```python
    # quiz 和 video 走独立流程，mindmap/summary/code 走类型资源生成，其他走 RAG + 编排
    is_quiz = (type == "quiz")
    is_video = (type == "video")
    is_type_resource = type in ("mindmap", "summary", "code")

    # 路由决策
    if is_quiz:
        intent = "generate_quiz"
        next_node = "quiz_generator"
    elif is_type_resource:
        intent = "generate_type_resource"
        next_node = NODE_RESOURCE_TYPE_GENERATOR
    else:
        intent = "generate_resource"
        next_node = "rag_retriever"
```

to:

```python
    # quiz 和 video 走独立流程，mindmap/summary/code 走类型资源生成，animation 走动画节点，其他走 RAG + 编排
    is_quiz = (type == "quiz")
    is_video = (type == "video")
    is_animation = (type == "animation")
    is_type_resource = type in ("mindmap", "summary", "code")

    # 路由决策
    if is_quiz:
        intent = "generate_quiz"
        next_node = "quiz_generator"
    elif is_animation:
        intent = "generate_animation"
        next_node = NODE_ANIMATION_SKILL_GENERATOR
    elif is_type_resource:
        intent = "generate_type_resource"
        next_node = NODE_RESOURCE_TYPE_GENERATOR
    else:
        intent = "generate_resource"
        next_node = "rag_retriever"
```

- [ ] **Step 3: Verify import works**

```bash
cd Python-backend && python -c "from app.api.v1.endpoints.resource_chat import router; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 4: Commit**

```bash
git add Python-backend/app/api/v1/endpoints/resource_chat.py
git commit -m "feat: add type=animation routing to animation_skill_generator node"
```

---

### Task 6: End-to-End Smoke Test

**Files:** None (manual verification)

- [ ] **Step 1: Run all Python tests**

```bash
cd Python-backend && python -m pytest tests/ -v
```

Expected: All tests PASS (existing + new).

- [ ] **Step 2: Start the Python backend**

```bash
cd Python-backend && python main.py
```

Expected: Server starts on port 8002 without errors. Look for log line: `已注册 11 个节点`.

- [ ] **Step 3: Test the animation endpoint with curl**

```bash
curl -N "http://localhost:8002/api/ai/resource/generate?type=animation&moduleId=1&planId=1&userId=1" \
  -H "Authorization: Bearer test-ticket"
```

Expected: SSE stream begins with `resource_type_generated` event containing `module_type: "animation"`. (Will fail if Java backend is not running, but validates the routing works up to the LLM call.)

- [ ] **Step 4: Verify logs**

Check Python backend logs for:
- `[动画生成] 开始处理`
- `已加载 skill 'jacky-motion-main'`
- `[动画生成] 正在调用 LLM...`

This confirms the full path: resource_chat → controller → animation_skill_generator → skill loader → LLM call.
