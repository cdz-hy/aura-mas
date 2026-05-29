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
