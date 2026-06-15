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
from app.agents.llm_factory import get_note_format_llm
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

## 边栏批注（必须执行）

整理笔记时，你必须在正文中标注学生需要注意的地方。标注方法：在对应句子的句号后面插入一个批注标记。

批注标记格式为：<<A:编号|类型|批注文本>>

其中：
- 编号：从1开始递增的数字
- 类型：只能是这5种之一：易混淆、易错点、提醒、注意、技巧
- 批注文本：15-40字，具体说明需要注意什么

### 示例（你的输出必须包含这样的标记）

UDP 是无连接的运输层协议，发送数据前不需要建立连接。<<A:1|易混淆|注意和TCP的区别：TCP需要三次握手建立连接，UDP不需要>>

UDP 首部只有8字节，包含源端口、目的端口、长度、校验和四个字段。<<A:2|技巧|记忆口诀：源目长校，8字节四字段>>

UDP 的校验和在IPv6中是强制的。<<A:3|易错点|IPv4中校验和可选，但IPv6中强制，考试常考这个区别>>

### 硬性要求
- 每篇笔记至少标注2处，不能跳过
- <<A:编号|类型|文本>> 放在句号之后
- 标记是内容的一部分，必须输出

## 输出

直接输出整理后的 Markdown。输出中必须包含 <<A:编号|类型|文本>> 批注标记（见上方示例），这是内容的一部分。不要输出任何解释说明。"""


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
            # 认证（同步调用，放到线程池避免阻塞事件循环）
            user_info = await asyncio.to_thread(java_client.validate_ticket, req.ticket)
            user_id = user_info.get("userId") or user_info.get("user_id")
            if not user_id:
                yield f"data: {json.dumps({'type': 'error', 'content': '认证失败'}, ensure_ascii=False)}\n\n"
                return

            # 获取用户画像（同步调用，放到线程池）
            try:
                profile = await asyncio.to_thread(java_client.get_user_profile, user_id)
                behavior = profile.get("learning_behavior", {})
                behavior = ensure_learning_behavior_fields(behavior)
            except Exception:
                behavior = {}

            # 构造 prompt
            style_hints = _build_style_hints(behavior)
            system_prompt = FORMAT_PROMPT_BASE.format(
                style_hints=style_hints,
            )

            user_prompt = (
                "请整理以下笔记。注意：输出中必须包含 <<A:编号|类型|文本>> 批注标记，至少2处。\n\n"
                + req.content
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            yield f"data: {json.dumps({'type': 'progress', 'content': '正在整理笔记...'}, ensure_ascii=False)}\n\n"

            # 流式调用 LLM
            llm = get_note_format_llm()
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
