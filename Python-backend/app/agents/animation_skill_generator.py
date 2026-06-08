"""
动画 Skill 生成智能体节点 — 读取 jacky-motion-main skill 文件，LLM 直出完整 HTML

架构：LLM 按 skill 指令直接生成完整 HTML 页面，不再通过 animationSpec JSON + 模板注入
流程：load skill → 选风格 → 摘要源内容 → 组装 prompt → LLM 直接生成完整 HTML → 提取 HTML → 返回
"""
import logging
import html
import os
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from typing import Dict, Any, Tuple

from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_type_generator_llm
from app.skills.loader import load_skill
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("agents.animation_skill_generator")

# ── 常量 ──
DEFAULT_STYLE = "apple-tech-gradient"
ANIMATION_SKILL_NAME = "jacky-motion-main"
ANIMATION_HTML_MAX_TOKENS = 32768
FALLBACK_DURATION = 45
ANIMATION_REQUEST_TIMEOUT = 300
MAX_SOURCE_CONTENT_LENGTH = 6000
ANIMATION_JS_RETRY_MAX = 1  # JS 语法错误时最多重试次数


def _resolve_node_bin() -> str | None:
    configured = os.environ.get("NODE_BIN")
    if configured:
        return configured
    return shutil.which("node")


NODE_BIN = _resolve_node_bin()


JS_SCRIPT_TYPES = {
    "application/ecmascript",
    "application/javascript",
    "application/x-ecmascript",
    "application/x-javascript",
    "text/ecmascript",
    "text/javascript",
    "text/javascript1.0",
    "text/javascript1.1",
    "text/javascript1.2",
    "text/javascript1.3",
    "text/javascript1.4",
    "text/javascript1.5",
    "text/jscript",
    "text/livescript",
    "text/x-ecmascript",
    "text/x-javascript",
}


def _get_script_attr(attrs: str, attr_name: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(attr_name)}\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+))",
        attrs,
        re.IGNORECASE,
    )
    if not match:
        return None
    return next((group for group in match.groups() if group is not None), None)


def _is_javascript_script(attrs: str) -> bool:
    """Return True for inline classic JavaScript and module scripts."""
    if _get_script_attr(attrs, "src"):
        return False

    script_type = _get_script_attr(attrs, "type")
    if not script_type:
        return True

    normalized = script_type.split(";", 1)[0].strip().lower()
    return normalized == "module" or normalized in JS_SCRIPT_TYPES


class _AnimationHtmlContractParser(HTMLParser):
    """Collect real HTML tags and attributes for animation contract checks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.start_tags: list[tuple[str, dict[str, str]]] = []
        self.end_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {
            name.lower(): value or ""
            for name, value in attrs
            if name
        }
        self.start_tags.append((tag.lower(), attr_map))

    def handle_endtag(self, tag: str) -> None:
        self.end_tags.append(tag.lower())


def _parse_animation_html(html_content: str) -> _AnimationHtmlContractParser:
    parser = _AnimationHtmlContractParser()
    parser.feed(html_content)
    parser.close()
    return parser


def _class_tokens(class_value: str) -> set[str]:
    return {
        token.lower()
        for token in re.split(r"\s+", class_value)
        if token
    }


def _select_style_by_profile(user_profile: dict, override_style: str | None = None) -> str:
    """根据用户画像选择动画风格，支持通过 override_style 显式覆盖"""
    if override_style:
        return override_style

    behavior = user_profile.get("learning_behavior", {})
    vv = behavior.get("visual_vs_verbal", 0)
    sg = behavior.get("sequential_vs_global", 0)

    if vv < -0.3:
        return "apple-tech-gradient"
    if sg < -0.3:
        return "editorial-magazine"
    if sg > 0.3:
        return "newspaper-evidence"

    return DEFAULT_STYLE


def _clean_text(value: Any, default: str = "") -> str:
    """清洗文本：去除空白，合并空格"""
    text = str(value or default).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _shorten(value: Any, limit: int, default: str = "") -> str:
    """截断文本到指定长度，超出加省略号"""
    text = _clean_text(value, default)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _escape(value: Any) -> str:
    """HTML 转义"""
    return html.escape(str(value or ""), quote=True)


def _summarize_source_content(source_content: str, state: AgentState) -> str:
    """如果源内容过长，使用 LLM 摘要提取关键段；失败则降级为截断"""
    if len(source_content) <= MAX_SOURCE_CONTENT_LENGTH:
        return source_content

    logger.info(f"  [动画生成] 源内容过长({len(source_content)}字符)，尝试 LLM 摘要...")

    try:
        llm = get_resource_type_generator_llm()
        summary_messages = [
            {
                "role": "system",
                "content": "你是教学动画内容提取助手。请输出 JSON: {\"summary\": \"摘要内容\"}",
            },
            {
                "role": "user",
                "content": (
                    "请从以下学习资源中提取适合制作教学动画的关键内容，"
                    "保留核心概念、流程步骤和关系结构，控制在 3000 字以内。\n\n"
                    + source_content
                ),
            },
        ]
        result = llm.chat_json(summary_messages, max_tokens=1024)
        record_from_mimo(
            llm,
            state.get("user_id", 0),
            "animation_summarization",
            state.get("task_id"),
        )
        summarized = result.get("summary", "") if isinstance(result, dict) else ""
        if summarized:
            logger.info(
                f"  [动画生成] 源内容已摘要: {len(source_content)} → {len(summarized)} 字符"
            )
            return summarized
    except Exception as e:
        logger.warning(f"  [动画生成] 源内容摘要失败，降级为截断: {e}")

    # 降级：简单截断
    return source_content[:MAX_SOURCE_CONTENT_LENGTH] + (
        f"\n\n... (源内容共 {len(source_content)} 字符，已截断)"
    )


def _extract_html_from_response(response: str) -> str:
    """从 LLM 响应中提取 HTML 内容

    提取优先级:
    1. ```html ... ``` 代码块
    2. <!doctype html> 或 <html 标签开始
    3. 整个响应就是 HTML
    """
    if not response or not response.strip():
        return ""

    text = response.strip()

    # 尝试提取 markdown 代码块中的 HTML
    html_block_match = re.search(
        r"```html\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE
    )
    if html_block_match:
        return html_block_match.group(1).strip()

    # 也尝试不带语言标记的代码块
    code_block_match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if code_block_match:
        block_content = code_block_match.group(1).strip()
        if block_content.lower().startswith("<!doctype") or block_content.lower().startswith("<html"):
            return block_content

    # 尝试从文本中找到 HTML 起始位置
    doctype_idx = text.lower().find("<!doctype html")
    html_tag_idx = text.lower().find("<html")

    if doctype_idx != -1:
        # 从 <!doctype html> 开始提取到 </html> 结束
        html_end = text.lower().find("</html>", doctype_idx)
        if html_end != -1:
            return text[doctype_idx : html_end + len("</html>")].strip()
        return text[doctype_idx:].strip()

    if html_tag_idx != -1:
        html_end = text.lower().find("</html>", html_tag_idx)
        if html_end != -1:
            return text[html_tag_idx : html_end + len("</html>")].strip()
        return text[html_tag_idx:].strip()

    # 如果整个响应看起来像 HTML（以 < 开头），直接返回
    if text.startswith("<") and ("</body>" in text.lower() or "</html>" in text.lower()):
        return text

    return ""


def _validate_js_syntax(html_content: str) -> Tuple[bool, str]:
    """使用 Node.js --check 验证 HTML 中 <script> 标签的 JS 语法

    Returns:
        (is_valid, error_message)
    """
    if not html_content:
        return True, ""

    # 提取所有 inline JavaScript <script> 标签中的 JS 代码
    script_blocks = re.findall(
        r"<script\b([^>]*)>(.*?)</script>", html_content, re.DOTALL | re.IGNORECASE
    )

    if not script_blocks:
        return True, ""

    # 合并所有 classic/module JS script 块进行检查，跳过 JSON-LD/importmap 等数据脚本
    js_code_parts = []
    for attrs, block in script_blocks:
        if not _is_javascript_script(attrs):
            continue
        stripped = block.strip()
        if not stripped:
            continue
        js_code_parts.append(stripped)

    if not js_code_parts:
        return True, ""

    combined_js = "\n;\n".join(js_code_parts)

    if not NODE_BIN:
        logger.warning("  [JS验证] Node.js 未找到，跳过 JS 语法验证")
        return True, ""

    # 写入临时文件用 Node.js --check 检查
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as f:
            f.write(combined_js)
            temp_path = f.name

        try:
            result = subprocess.run(
                [NODE_BIN, "--check", temp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, ""
            else:
                error_msg = result.stderr.strip()
                # 提取关键错误信息（去掉文件路径，只保留错误描述）
                # Node.js 输出格式: "file.js:line:col\n\nSyntaxError: ..."
                syntax_error_match = re.search(
                    r"SyntaxError:.*", error_msg, re.DOTALL
                )
                if syntax_error_match:
                    return False, syntax_error_match.group(0).strip()
                return False, error_msg[:300]
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    except FileNotFoundError:
        logger.warning("  [JS验证] Node.js 未找到，跳过 JS 语法验证")
        return True, ""
    except subprocess.TimeoutExpired:
        logger.warning("  [JS验证] Node.js --check 超时，跳过验证")
        return True, ""
    except Exception as e:
        logger.warning(f"  [JS验证] 验证过程异常，跳过: {e}")
        return True, ""


def _validate_animation_html_contract(html_content: str) -> Tuple[bool, str]:
    """Validate structural requirements that prevent common animation black screens."""
    if not html_content or not html_content.strip():
        return False, "HTML is empty"

    parser = _parse_animation_html(html_content)
    start_tags = parser.start_tags
    html_start = any(tag == "html" for tag, _ in start_tags)
    html_end = "html" in parser.end_tags
    if not html_start or not html_end:
        return False, "HTML must include <html> and </html>"

    has_stage = any(attrs.get("id", "").lower() == "stage" for _, attrs in start_tags)
    if not has_stage:
        return False, "Animation HTML must include #stage"

    class_token_sets = [
        _class_tokens(attrs.get("class", ""))
        for _, attrs in start_tags
        if attrs.get("class")
    ]
    if not any("beat" in class_tokens for class_tokens in class_token_sets):
        return False, "Animation HTML must include at least one .beat"
    if not any(
        {"beat", "active"}.issubset(class_tokens)
        for class_tokens in class_token_sets
    ):
        return False, "Animation HTML must mark an initial active beat"

    has_gsap_script = any(
        tag == "script"
        and "src" in attrs
        and "gsap" in attrs["src"].lower()
        and attrs["src"].lower().split("?", 1)[0].split("#", 1)[0].endswith(".js")
        for tag, attrs in start_tags
    )
    if not has_gsap_script:
        return False, "Animation HTML must include a GSAP <script src=\"...gsap...js\"> reference"
    return True, ""


GSAP_HALLUCINATION_PATTERNS = [
    (r'\btl\.labels\s*\(', "tl.labels is a property (object), not a function — use Object.keys(tl.labels) or tl.labels['name']"),
    (r'\.labels\s*\(\s*\)', ".labels() is invalid — labels is a property, not a method"),
    (r'\bgsap\.timeline\s*\.\s*to\b', "gsap.timeline.to is invalid — create instance first: const tl = gsap.timeline(); tl.to(...)"),
    (r'\bgsap\.set\s*\(\s*["\']\.beat["\'].*autoAlpha\s*:\s*0', "gsap.set('.beat', {autoAlpha:0}) hides all beats permanently if timeline fails — use CSS visibility instead"),
    (r'\bon(?:click|mouseover|mouseout|mousedown|mouseup|touchstart|touchend)\s*=\s*["\']', "Inline event handlers (onclick=...) execute in global scope and cannot access functions inside IIFE/module closures — use addEventListener instead"),
]


def _validate_gsap_api_usage(html_content: str) -> Tuple[bool, str]:
    """Catch common LLM hallucinations about GSAP API."""
    for pattern, message in GSAP_HALLUCINATION_PATTERNS:
        if re.search(pattern, html_content):
            return False, message
    return True, ""


def _build_fallback_html(title: str, description: str, source_content: str) -> str:
    """LLM 失败时的最小降级 HTML

    纯 HTML+CSS，无 GSAP。简单的 beat 切换。
    基于苹果科技风暗色配色。
    """
    # 按段落拆分源内容，生成 3 个 beat
    paragraphs = [
        _shorten(p, 120)
        for p in re.split(r"\n+|(?<=[。！？])", source_content)
        if _clean_text(p)
    ]
    if not paragraphs:
        paragraphs = [_shorten(title, 120, "核心概念")]

    labels = ["先建立整体图景", "再拆解关键关系", "最后形成可迁移理解"]
    beats_data = []
    for idx in range(3):
        idea = paragraphs[idx] if idx < len(paragraphs) else paragraphs[-1]
        beats_data.append({
            "label": labels[idx],
            "idea": idea,
        })

    beat_sections = []
    for idx, beat in enumerate(beats_data, start=1):
        active_class = " active" if idx == 1 else ""
        beat_sections.append(
            f'<div class="beat{active_class}">\n'
            f'  <span class="beat-tag">Beat {idx}/3</span>\n'
            f'  <h2>{_escape(beat["label"])}</h2>\n'
            f'  <p>{_escape(beat["idea"])}</p>\n'
            f'</div>'
        )

    beats_html = "\n".join(beat_sections)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape(title)}</title>
<style>
  :root {{
    --bg: #050505;
    --fg: #f5f5f7;
    --muted: rgba(245,245,247,0.6);
    --accent: #e85d36;
    --card: rgba(255,255,255,0.04);
    --radius: 16px;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: var(--bg);
    color: var(--fg);
    font-family: -apple-system, 'Noto Sans SC', sans-serif;
    display: grid;
    place-items: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .beat {{
    display: none;
    padding: 8vh 6vw;
    max-width: 900px;
  }}
  .beat.active {{ display: block; }}
  .beat-tag {{
    color: var(--accent);
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 16px;
    display: inline-block;
  }}
  h2 {{
    font-size: clamp(28px, 4vw, 42px);
    font-weight: 700;
    margin-bottom: 16px;
    line-height: 1.2;
  }}
  p {{
    color: var(--muted);
    font-size: clamp(16px, 1.5vw, 20px);
    line-height: 1.6;
  }}
</style>
</head>
<body>
{beats_html}
<script>
  const beats = document.querySelectorAll('.beat');
  let current = 0;
  setInterval(() => {{
    beats[current].classList.remove('active');
    current = (current + 1) % beats.length;
    beats[current].classList.add('active');
  }}, 5000);
</script>
</body>
</html>"""


def _extract_css_dna(template_html: str) -> str:
    """从风格模板 HTML 中精简提取 CSS DNA（:root 变量 + 组件类），去除 HTML 结构/JS/注释

    模板文件注释说"这不是模板，不要复制 HTML 结构"，LLM 只需要 CSS 变量和组件类。
    精简后可减少 ~50% 的 token 消耗，加速 LLM 生成。
    """
    if not template_html:
        return ""

    # 提取 <style> 标签内的内容
    style_match = re.search(r"<style[^>]*>(.*?)</style>", template_html, re.DOTALL | re.IGNORECASE)
    if not style_match:
        return template_html

    css_text = style_match.group(1)

    # 去除 CSS 注释
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)

    # 去除 @import 整行（含 url() 形式，可能跨行）
    css_text = re.sub(r"@import\s+url\([^)]*\)\s*;?", "", css_text)
    css_text = re.sub(r"@import\s+[^;]+;", "", css_text)
    # 清理 @import url 残余（如 '); 或单独的 url() 行）
    css_text = re.sub(r"^\s*[^@/{}\n]*url\([^)]*\)\s*;?\s*$", "", css_text, flags=re.MULTILINE)

    # 逐规则块提取：只保留 :root 和组件类（.xxx），排除 .beat / #stage / body / html 等
    kept_blocks = []
    # 用正则按 {} 顶层匹配 CSS 规则块
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_text):
        selector = m.group(1).strip()
        block_body = m.group(2).strip()

        # 跳过空选择器或非标准选择器（@import 残留等）
        if not selector or selector.startswith("@") or "url(" in selector:
            continue

        # 保留 :root
        if ":root" in selector:
            kept_blocks.append(f"{selector} {{\n{block_body}\n}}")
            continue

        # 保留组件类（以 . 开头，排除结构类）
        skip_prefixes = (".beat", "#stage", "#nav", "body", "html", "*", "::")
        if any(selector.startswith(p) for p in skip_prefixes):
            continue

        if selector.startswith("."):
            kept_blocks.append(f"{selector} {{\n{block_body}\n}}")
            continue

    result = "\n\n".join(kept_blocks)

    # 清理残留的非规则行（@import url 尾部等）
    result = re.sub(r"^[^\n{}]*url\([^)]*\)[^{]*$", "", result, flags=re.MULTILINE)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()

    # 如果精简后太短，回退用原文
    if len(result) < 200:
        logger.debug(f"  [动画生成] CSS DNA 精简后过短({len(result)}字符)，回退用原始模板")
        return template_html

    logger.debug(f"  [动画生成] CSS DNA 精简: {len(template_html)} → {len(result)} 字符")
    return result


def _assemble_system_prompt(
    skill_md: str,
    style_rules: str,
    css_dna: str,
    script_audit: str,
    quality_check: str,
) -> str:
    """组装全自动模式的 system prompt"""
    parts = []

    # 主指令：SKILL.md
    parts.append("# 科普动画导演 — 全自动模式\n\n")
    parts.append("你是一个科普动画导演，按照以下 skill 流水线把口播稿变成可录屏的 16:9 信息动画 HTML。\n\n")
    parts.append("## 重要：全自动模式\n\n")
    parts.append("用户要求全自动生成。跳过所有确认门（审稿确认、分镜确认、风格确认），自动完成所有阶段，直接输出最终 HTML。\n")
    parts.append("流程：审稿(自动) → 分镜(自动) → 锁风格(已选) → 生成HTML → 验收(自动) → 输出\n\n")

    # SKILL.md
    parts.append("## Skill 流水线规则\n\n")
    parts.append(skill_md)

    # 审稿标准
    if script_audit:
        parts.append("\n\n## 审稿标准 (Phase 1)\n\n")
        parts.append(script_audit)

    # 风格规则
    if style_rules:
        parts.append("\n\n## 当前风格规则 (Phase 3 已锁定)\n\n")
        parts.append(style_rules)

    # CSS DNA
    if css_dna:
        parts.append("\n\n## CSS DNA 参考 (Phase 4)\n\n")
        parts.append("以下是风格模板的 CSS 变量和组件类。读取并使用这些变量和类来构建 HTML，")
        parts.append("但不要直接复制 HTML 结构——为每个 beat 编写独立的 CSS 类和 GSAP 动画。\n\n")
        parts.append(_extract_css_dna(css_dna))

    # 质量检查
    if quality_check:
        parts.append("\n\n## 交付前验收检查 (Phase 5)\n\n")
        parts.append("生成 HTML 前逐条对照，不通过的先修复再输出。\n\n")
        parts.append(quality_check)

    # 输出格式
    parts.append("\n\n## 输出要求\n\n")
    parts.append("1. 直接输出完整单文件 HTML（包含 DOCTYPE、head、body、所有 CSS、所有 GSAP 动画 JS）\n")
    parts.append("2. 不要用 Markdown 代码块包裹，不要加 ```html 标记\n")
    parts.append("3. 不要输出任何解释文字，只输出 HTML\n")
    parts.append("4. GSAP 3 via CDN: https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js\n")
    parts.append("5. 字体: Google Fonts Inter + Noto Sans SC\n\n")

    # JS 语法正确性要求
    parts.append("## JavaScript 语法硬性要求（不通过 = 动画黑屏）\n\n")
    parts.append("1. 所有 <script> 中的 JS 代码必须语法正确，括号、花括号、方括号必须配对\n")
    parts.append("2. 每个 GSAP gsap.to()/gsap.from()/gsap.timeline() 调用的参数列表必须完整闭合\n")
    parts.append("3. 不要使用模板字面量中的未转义反引号，避免和 HTML 外层冲突\n")
    parts.append("4. 确保 gsap.to() 的 target 选择器在 HTML 中有对应元素——不要凭空引用不存在的 class\n")
    parts.append("5. 生成后自行在心里检查一遍：每个 ( 都有配对的 )，每个 { 都有配对的 }\n")

    return "".join(parts)


def _assemble_user_message(
    source_title: str,
    source_content: str,
    user_profile: dict,
    selected_style: str,
) -> str:
    """组装 user message"""
    behavior = user_profile.get("learning_behavior", {})
    vv = behavior.get("visual_vs_verbal", 0)
    sg = behavior.get("sequential_vs_global", 0)

    vv_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")
    sg_text = "序列型" if sg < -0.3 else ("全局型" if sg > 0.3 else "均衡型")

    return f"""请基于以下内容生成科普动画 HTML。

## 口播稿/源内容标题
{source_title}

## 口播稿/源内容正文
{source_content}

## 用户偏好
- 视觉/言语倾向: {vv_text}
- 序列/全局倾向: {sg_text}

## 风格
使用 {selected_style} 风格。

请走全自动流水线，直接输出完整 HTML。"""


def animation_skill_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    动画 Skill 生成节点 — LLM 直出完整 HTML

    1. 从 state 取源资源内容和用户画像
    2. 加载 jacky-motion-main skill 文件
    3. 选风格（画像驱动 + 覆盖）
    4. 源内容过长则摘要
    5. 组装完整 prompt（SKILL.md + 风格规则 + CSS DNA + 审稿标准 + 质量检查）
    6. 调 LLM 直接生成完整 HTML
    7. 提取 HTML，失败则降级
    8. 返回 generated_content（向后兼容结构）
    """
    source_resource_content = state.get("source_resource_content", "")
    user_profile = state.get("user_profile", {})
    task_breakdown = state.get("task_breakdown") or {}

    # 从 task_breakdown 提取标题
    modules = task_breakdown.get("modules", [])
    module_title = ""
    if modules:
        module_title = modules[0].get("title", "")

    source_title = module_title or "未知资源"

    logger.info(f"{'='*60}")
    logger.info(f"  [动画生成] 开始处理 (jacky-motion 全自动模式)")
    logger.info(f"  源资源标题: {source_title}")
    if not source_resource_content:
        module_description = modules[0].get("description", "") if modules else ""
        source_resource_content = f"{source_title}\n\n{module_description}".strip()
        logger.warning(
            "  [动画生成] 源资源正文为空，使用标题/描述作为最小上下文 | "
            "plan_id=%s session_id=%s title=%s 内容长度=%d",
            state.get("plan_id"), state.get("session_id"),
            source_title, len(source_resource_content),
        )
    logger.info(f"  源资源内容长度: {len(source_resource_content)} 字符")

    # ── 阶段 1：加载动画技能包 ──
    stream_events: list[dict] = [{
        "event_type": "thinking",
        "agent": "animation_skill_generator",
        "data": {"message": "正在加载动画技能包..."},
        "step_description": "加载动画技能包",
    }]

    try:
        skill = load_skill(ANIMATION_SKILL_NAME)
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

    # ── 多风格选择：画像驱动 + 覆盖 ──
    override_style = state.get("animation_style")
    selected_style = _select_style_by_profile(user_profile, override_style)
    logger.info(f"  [动画生成] 选中风格: {selected_style} (override={override_style})")

    # 获取风格规则（styles/*.md）
    style_rules = skill.styles.get(selected_style, "")
    if not style_rules:
        logger.warning(f"  [动画生成] 风格 {selected_style} 规则为空，尝试默认风格")
        style_rules = skill.styles.get(DEFAULT_STYLE, "")

    # 获取 CSS DNA 参考（templates/*.html）
    css_dna = skill.templates.get(selected_style, "")
    if not css_dna:
        logger.warning(f"  [动画生成] 风格 {selected_style} 模板为空，尝试默认风格")
        css_dna = skill.templates.get(DEFAULT_STYLE, "")

    # 获取审稿标准和质量检查
    script_audit = skill.references.get("script-audit", "")
    quality_check = skill.references.get("quality-check", "")

    # ── 阶段 2：构思动画结构 ──
    stream_events.append({
        "event_type": "thinking",
        "agent": "animation_skill_generator",
        "data": {"message": "正在构思动画结构..."},
        "step_description": "构思动画结构",
    })

    # ── 源内容智能处理：过长则摘要 ──
    processed_content = _summarize_source_content(source_resource_content, state)

    # 组装 prompt
    system_prompt = _assemble_system_prompt(
        skill_md=skill.skill_md,
        style_rules=style_rules,
        css_dna=css_dna,
        script_audit=script_audit,
        quality_check=quality_check,
    )
    user_message = _assemble_user_message(
        source_title=source_title,
        source_content=processed_content,
        user_profile=user_profile,
        selected_style=selected_style,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    llm_failed = False
    llm_error = ""
    html_output = ""
    js_retry_count = 0

    # ── 阶段 3：LLM 直出完整 HTML（支持 JS 语法验证 + 重试） ──
    stream_events.append({
        "event_type": "thinking",
        "agent": "animation_skill_generator",
        "data": {"message": "正在生成动画 HTML..."},
        "step_description": "生成动画 HTML",
    })

    while True:
        try:
            llm = get_resource_type_generator_llm()
            llm.request_timeout = ANIMATION_REQUEST_TIMEOUT
            logger.info("  [动画生成] 正在调用 LLM 流式生成完整 HTML...")

            # 使用流式生成避免长输出超时
            response_chunks = []
            chunk_count = 0
            for chunk in llm.chat_stream(messages, max_tokens=ANIMATION_HTML_MAX_TOKENS):
                response_chunks.append(chunk)
                chunk_count += 1
                if chunk_count % 100 == 0:
                    logger.debug(f"  [动画生成] 已接收 {chunk_count} 个 chunk，累积 {sum(len(c) for c in response_chunks)} 字符")

            response = "".join(response_chunks)
            record_from_mimo(llm, state.get("user_id", 0), "animation_generation", state.get("task_id"))

            logger.info(f"  [动画生成] LLM 流式生成完成，共 {chunk_count} 个 chunk，总长 {len(response)} 字符")

            # 从响应中提取 HTML
            html_output = _extract_html_from_response(response)

            if not html_output:
                logger.warning("  [动画生成] LLM 响应中未提取到有效 HTML，使用降级 HTML")
                llm_failed = True
                llm_error = "LLM 响应中未包含有效 HTML"
                html_output = _build_fallback_html(
                    title=source_title,
                    description="",
                    source_content=source_resource_content,
                )
                break

            logger.info(f"  [动画生成] 成功提取 HTML，长度: {len(html_output)} 字符")

            # ── HTML 验证（JS 语法 + GSAP API 正确性 + 动画结构契约） ──
            is_valid, validation_error = _validate_js_syntax(html_output)
            if is_valid:
                gsap_valid, gsap_error = _validate_gsap_api_usage(html_output)
                if not gsap_valid:
                    validation_error = gsap_error
                    logger.warning(f"  [动画生成] GSAP API 幻觉检测: {gsap_error}")
                else:
                    contract_valid, contract_error = _validate_animation_html_contract(html_output)
                    if contract_valid:
                        logger.info("  [动画生成] JS 语法 + GSAP API + 结构契约验证通过 ✓")
                        break
                    validation_error = contract_error
                    logger.warning(f"  [动画生成] HTML 结构验证失败: {contract_error}")
            else:
                logger.warning(f"  [动画生成] JS 语法验证失败: {validation_error}")

            # HTML 验证失败 → 判断是否可重试
            logger.warning(f"  [动画生成] HTML 验证失败: {validation_error[:200]}")

            if js_retry_count < ANIMATION_JS_RETRY_MAX:
                js_retry_count += 1
                logger.info(f"  [动画生成] 尝试第 {js_retry_count} 次 HTML 修复重试...")

                # 把错误信息反馈给 LLM，让它修复
                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": (
                        f"HTML validation failed for the animation output.\n\n"
                        f"**Validation error**: {validation_error}\n\n"
                        f"请修复这个 HTML，重新输出完整单文件 HTML。\n"
                        f"特别注意：\n"
                        f"1. 保留 <html>...</html>、#stage、至少一个 .beat，且初始 .beat 同时包含 active\n"
                        f"2. 使用 <script src=\"...gsap...js\"></script> 引入 GSAP\n"
                        f"3. 检查所有 JavaScript 括号、花括号、方括号是否配对\n"
                        f"4. 确保 gsap.to() / gsap.from() 的 target 选择器在 HTML 中有对应元素\n"
                        f"5. tl.labels 是属性（对象），不是函数，不要写 tl.labels()\n"
                        f"6. gsap.timeline() 没有 .add(labelName) 签名，用 tl.addLabel(name, position)\n"
                        f"7. gsap.effects 需要先注册才能用，不要调用未注册的 effect\n"
                    ),
                })
                continue
            else:
                logger.warning(f"  [动画生成] HTML 修复重试已达上限({ANIMATION_JS_RETRY_MAX})，使用降级 HTML")
                llm_failed = True
                llm_error = f"HTML 验证失败，重试 {js_retry_count} 次仍未修复: {validation_error[:120]}"
                html_output = _build_fallback_html(
                    title=source_title,
                    description="",
                    source_content=source_resource_content,
                )
                break

        except Exception as e:
            llm_failed = True
            llm_error = str(e)
            logger.warning("  [动画生成] LLM 调用失败，使用降级 HTML: %s", llm_error)
            html_output = _build_fallback_html(
                title=source_title,
                description="",
                source_content=source_resource_content,
            )
            break

    # 构造输出（向后兼容结构）
    title = f"{source_title} - 动画演示"
    description = "基于源资源自动生成的科普动画。"

    generated = {
        "module_type": "animation",
        "title": title,
        "description": description,
        "html": html_output,
        "content": html_output,  # 兼容
        "animationSpec": None,   # 不再有 animationSpec
        "duration": 60,
        "metadata": {
            "renderer": "jacky-motion",
            "version": "3.0",
            "source": "current_resource",
            "interactive": True,
            "fallback": llm_failed,
            "style": selected_style,
        },
    }

    logger.info(f"  [动画生成] 生成完成!")
    logger.info(f"    标题: {generated['title']}")
    logger.info(f"    风格: {selected_style}")
    logger.info(f"    HTML 长度: {len(html_output)} 字符")
    logger.info(f"    降级: {llm_failed}")
    logger.info(f"    JS 修复重试: {js_retry_count} 次")
    if llm_failed:
        logger.info(f"    降级原因: {llm_error[:120]}")
    logger.info(f"{'='*60}")

    # 最终事件
    stream_events.append({
        "event_type": "resource_type_generated",
        "agent": "animation_skill_generator",
        "data": generated,
        "step_description": f"已生成动画资源",
    })

    return {
        "generated_content": generated,
        "current_step": f"动画生成: 已生成动画资源「{generated['title']}」",
        "stream_events": stream_events,
    }
