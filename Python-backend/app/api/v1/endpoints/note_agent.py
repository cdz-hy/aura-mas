"""
笔记智能整理 API - 将杂乱笔记内容整理为结构化 Markdown
SSE 流式输出整理结果
"""
import json
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.db.java_client import java_client
from app.agents.llm_factory import get_simple_answer_llm
from app.utils.profile_utils import ensure_learning_behavior_fields
from app.skills.loader import load_skill
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("api.note_agent")
router = APIRouter()


class FormatRequest(BaseModel):
    ticket: str
    content: str

FORMAT_PROMPT_BASE = """你是一位潮流学习笔记整理师，擅长把杂乱内容变成让人眼前一亮的精美笔记。请将以下笔记内容整理为结构化 Markdown。

## 排版规范

### 1. Emoji 视觉标记
每个要点前加 emoji，让笔记活泼有层次：
- 🔑 核心概念 / 关键定义
- 📌 重点内容 / 必背知识
- 💡 小技巧 / 实用提示
- ⚠️ 易错点 / 注意事项
- 🌰 举例说明
- 📖 定义 / 术语解释
- 🔵 步骤流程（用 🔵 Step 1、🔵 Step 2...）
- ⚖️ 对比分析
- ✅ 总结结论

### 2. Callout 信息卡片
重要提示用 blockquote + emoji 前缀，形成醒目的信息卡片：
```
> 💡 **小技巧**：这里的提示内容
> ⚠️ **注意**：这里写易错点
> 📌 **重点**：这里写核心概念
> 🌰 **举个栗子**：这里写具体例子
> 🔑 **关键**：这里写核心原理
```

### 3. 排版节奏
- **短句分段**：每 2-3 句一个段落，段间留空行，增加呼吸感
- **关键词加粗**：重要术语用 `**加粗**` 高亮
- **行内代码**：专业术语、函数名、变量名用 `` ` ` ` `` 包裹
- **不要大段文字**：宁可多分段，也不要一大坨文字堆在一起

### 4. 结构化呈现
- 标题层级：`#` 一级 → `##` 二级 → `###` 三级
- 列表要点用 `- ` 无序列表
- 流程步骤用 `🔵 Step N:` 格式
- 有对比关系的内容用表格呈现
- 代码用 ``` 包裹并标注语言
- 数学公式用 $...$ 或 $$...$$

### 5. 开头概览
如果内容较多，在开头用 `> 📖 **一句话概括**：xxx` 给出整体概览

### 6. 末尾总结
在末尾添加 `## ✅ 一句话总结` 用 3-5 个 emoji 开头的要点精炼概括

## 核心原则

1. **保留原始语义**：不添加笔记中没有的信息，不改变原意
2. **去除冗余**：删除重复内容、无意义语气词、乱码
3. **逻辑分组**：相关内容归到同一标题下，有条有理
4. **视觉舒适**：排版要有节奏感，不要密密麻麻，也不要过于稀疏

## 学习风格适配

{style_hints}

## 输出

直接输出整理后的 Markdown，不要输出任何解释说明。

## Markdown 语法参考

以下是你要遵循的 Markdown 语法规范，请严格按照其中的格式要求输出：

{skill_reference}

## 思维导图生成

整理完笔记后，请根据笔记内容生成一个思维导图 JSON，帮助读者直观理解知识结构。

### 输出格式
在笔记 Markdown 的最末尾，用 ```mindmap 代码块包裹 MindElixir 格式的 JSON。

### MindElixir 数据格式
```json
{{
  "nodeData": {{
    "id": "root",
    "topic": "主题名称",
    "children": [
      {{
        "id": "unique_id_1",
        "topic": "分支1",
        "children": [
          {{ "id": "id_1_1", "topic": "子节点1" }},
          {{ "id": "id_1_2", "topic": "子节点2" }}
        ]
      }},
      {{
        "id": "unique_id_2",
        "topic": "分支2",
        "children": []
      }}
    ]
  }}
}}
```

### 要求
- topic 使用简短的关键词或短语，不要照搬笔记大段文字
- 根据笔记的标题层级构建树结构（标题=分支，要点=子节点）
- id 使用简短有意义的英文标识（如 "def_tree", "step_1"）
- 如果笔记内容太少（少于 3 个知识点），则不生成思维导图

### JSON Canvas 语法参考（备用）
如果你需要输出 JSON Canvas 格式供 Obsidian 使用，参考以下规范：

{canvas_reference}"""


def _build_style_hints(learning_behavior: dict) -> str:
    """根据用户学习风格生成整理提示"""
    hints = []
    vv = learning_behavior.get("visual_vs_verbal", 0)
    si = learning_behavior.get("sensing_vs_intuitive", 0)
    sg = learning_behavior.get("sequential_vs_global", 0)

    if vv < -0.2:
        hints.append("- 用户偏好视觉型学习：多用表格对比、流程图描述，在关键概念处标注 `[建议配图]`")
    elif vv > 0.2:
        hints.append("- 用户偏好言语型学习：展开详细文字解释，用完整的句子和比喻描述概念")

    if si < -0.2:
        hints.append("- 用户偏好感知型学习：多用 🌰 举具体实例和实际应用场景，贴近生活")
    elif si > 0.2:
        hints.append("- 用户偏好直觉型学习：先用 🔑 给出概念框架和核心原理，再补充细节")

    if sg < -0.2:
        hints.append("- 用户偏好循序型学习：用 🔵 Step N 严格按步骤排列，确保前后衔接")
    elif sg > 0.2:
        hints.append("- 用户偏好全局型学习：开头用 📖 给出概览大纲，先见森林再见树木")

    return "\n".join(hints) if hints else "无特殊偏好，按通用方式整理。"


@router.post("/note/format")
async def format_note(req: FormatRequest):
    """笔记智能整理 - SSE 流式返回整理后的 Markdown"""

    async def event_stream():
        try:
            # 认证
            user_info = java_client.validate_ticket(req.ticket)
            user_id = user_info.get("userId") or user_info.get("user_id")
            if not user_id:
                yield f"data: {json.dumps({'type': 'error', 'content': '认证失败'}, ensure_ascii=False)}\n\n"
                return

            # 获取用户画像
            try:
                profile = java_client.get_user_profile(user_id)
                behavior = profile.get("learning_behavior", {})
                behavior = ensure_learning_behavior_fields(behavior)
            except Exception:
                behavior = {}

            # 构造 prompt
            style_hints = _build_style_hints(behavior)
            try:
                md_skill = load_skill("obsidian-markdown")
                skill_reference = md_skill.skill_md
            except Exception as e:
                logger.warning(f"加载 obsidian-markdown skill 失败: {e}")
                skill_reference = ""
            try:
                canvas_skill = load_skill("json-canvas")
                canvas_reference = canvas_skill.skill_md
            except Exception as e:
                logger.warning(f"加载 json-canvas skill 失败: {e}")
                canvas_reference = ""
            system_prompt = FORMAT_PROMPT_BASE.format(
                style_hints=style_hints,
                skill_reference=skill_reference,
                canvas_reference=canvas_reference,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.content},
            ]

            yield f"data: {json.dumps({'type': 'progress', 'content': '正在整理笔记...'}, ensure_ascii=False)}\n\n"

            # 流式调用 LLM
            llm = get_simple_answer_llm()
            formatted = ""
            for chunk in llm.chat_stream(messages):
                if chunk:
                    formatted += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
            record_from_mimo(llm, user_id, "note_formatting")

            yield f"data: {json.dumps({'type': 'done', 'content': formatted}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"笔记整理失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
