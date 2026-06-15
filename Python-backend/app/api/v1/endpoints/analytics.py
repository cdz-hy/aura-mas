"""
学习分析 API - AI学习报告生成
"""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.llm_factory import get_simple_answer_llm
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger(__name__)
router = APIRouter()


class LearningReportRequest(BaseModel):
    """学习报告请求"""
    overview: Dict[str, Any] = {}
    quiz_analysis: Dict[str, Any] = {}
    heatmap: Dict[str, Any] = {}
    flashcard_stats: Dict[str, Any] = {}
    ai_interaction: Dict[str, Any] = {}
    knowledge_mastery: Dict[str, Any] = {}
    learning_style: Dict[str, Any] = {}


REPORT_PROMPT = """你是一位资深的学习分析专家和教育顾问。请根据以下学生的学习数据，生成一份个性化、有深度、有温度的学习分析报告。

## 学生学习数据

### 学习概况
- 今日学习时长: {today_duration}
- 累计学习时长: {total_duration}
- 学习计划: 总{total_plans}个，进行中{active_plans}个，已完成{completed_plans}个
- 学习资源完成率: {resource_completion}

### 答题表现
- 总答题数: {total_quizzes}
- 正确率: {quiz_accuracy}%
- 近期趋势: {quiz_trend}

### 学习连续性
- 当前连续学习: {current_streak}天
- 最长连续: {longest_streak}天
- 总活跃天数: {active_days}天

### 闪卡复习
- 总闪卡: {total_cards}张
- 待复习: {due_today}张
- 已掌握: {mastered}张

### 知识掌握
- 已掌握: {mastered_knowledge}
- 薄弱点: {weak_areas}
- 兴趣: {interests}

### 学习风格
- 视觉/言语: {visual_vs_verbal}
- 活跃/沉思: {active_vs_reflective}
- 感知/直觉: {sensing_vs_intuitive}
- 序列/全局: {sequential_vs_global}

## 报告要求

请用温暖、鼓励但实事求是的语气，生成一份包含以下部分的学习报告：

1. **学习概况总结** - 用1-2句话概括学习状态
2. **亮点与进步** - 指出做得好的地方
3. **需要改进的地方** - 温和地指出不足
4. **学习风格建议** - 基于学习风格给出具体建议
5. **下一步行动** - 给出3-5条可执行的建议

使用 Markdown 格式，包含标题和列表。"""


SUGGESTIONS_PROMPT = """你是一位温暖的学习教练。请根据以下学生的学习数据，给出 3 条简短的学习建议。

## 学生学习数据
- 今日学习时长: {today_duration}
- 累计学习时长: {total_duration}
- 答题正确率: {quiz_accuracy}%
- 正确率趋势: {quiz_trend}
- 当前连续学习: {current_streak}天
- 最长连续: {longest_streak}天
- 待复习闪卡: {due_today}张
- 已掌握知识: {mastered_knowledge}
- 薄弱知识点: {weak_areas}
- 兴趣方向: {interests}
- 学习风格: 视觉/言语={visual_vs_verbal}, 活跃/沉思={active_vs_reflective}

## 要求
- 每条建议 15-30 字，简洁有力
- 基于数据给出具体、可执行的建议
- 语气温暖鼓励，不要说教
- 每条建议附带一个 emoji 前缀

请严格按以下 JSON 格式返回，不要添加任何其他文字:
{{"suggestions": [{{"emoji": "🔥", "text": "建议内容"}}, {{"emoji": "📈", "text": "建议内容"}}, {{"emoji": "💡", "text": "建议内容"}}]}}"""


@router.post("/ai-suggestions")
async def generate_ai_suggestions(request: LearningReportRequest):
    """生成AI学习建议（SSE流式返回JSON）"""

    async def generate():
        try:
            overview = request.overview or {}
            quiz = request.quiz_analysis or {}
            heatmap = request.heatmap or {}
            flashcard = request.flashcard_stats or {}
            knowledge = request.knowledge_mastery or {}
            style = request.learning_style or {}

            prompt = SUGGESTIONS_PROMPT.format(
                today_duration=f"{overview.get('todayDurationSeconds', 0) // 60}分钟",
                total_duration=f"{overview.get('totalStudyHours', 0)}小时",
                quiz_accuracy=overview.get('quizAccuracy', 0),
                quiz_trend=quiz.get('recentTrend', {}).get('direction', '稳定'),
                current_streak=heatmap.get('currentStreak', 0),
                longest_streak=heatmap.get('longestStreak', 0),
                due_today=flashcard.get('dueToday', 0),
                mastered_knowledge='、'.join(knowledge.get('mastered', [])[:5]) or '暂无',
                weak_areas='、'.join(knowledge.get('weakAreas', [])[:5]) or '暂无',
                interests='、'.join(knowledge.get('interests', [])[:5]) or '暂无',
                visual_vs_verbal=style.get('visual_vs_verbal', 0),
                active_vs_reflective=style.get('active_vs_reflective', 0),
            )

            llm = get_simple_answer_llm()
            content = ""
            for chunk in llm.chat_stream([{"role": "user", "content": prompt}]):
                if chunk:
                    content += chunk
            record_from_mimo(llm, 0, "analytics_suggestions")

            yield f"data: {json.dumps({'type': 'done', 'content': content}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"生成AI建议失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/learning-report")
async def generate_learning_report(request: LearningReportRequest):
    """生成AI学习报告（SSE流式返回）"""

    async def generate():
        try:
            # 准备prompt数据
            overview = request.overview or {}
            quiz = request.quiz_analysis or {}
            heatmap = request.heatmap or {}
            flashcard = request.flashcard_stats or {}
            knowledge = request.knowledge_mastery or {}

            # 提取学习风格维度（从 learning_style 字段获取）
            style = request.learning_style or {}

            prompt = REPORT_PROMPT.format(
                today_duration=f"{overview.get('todayDurationSeconds', 0) // 60}分钟",
                total_duration=f"{overview.get('totalStudyHours', 0)}小时",
                total_plans=overview.get('totalPlans', 0),
                active_plans=overview.get('activePlans', 0),
                completed_plans=overview.get('completedPlans', 0),
                resource_completion=f"{overview.get('completedResources', 0)}/{overview.get('totalResources', 0)}",
                total_quizzes=overview.get('totalQuizzes', 0),
                quiz_accuracy=overview.get('quizAccuracy', 0),
                quiz_trend=quiz.get('recentTrend', {}).get('direction', '稳定'),
                current_streak=heatmap.get('currentStreak', 0),
                longest_streak=heatmap.get('longestStreak', 0),
                active_days=heatmap.get('totalActiveDays', 0),
                total_cards=flashcard.get('totalCards', 0),
                due_today=flashcard.get('dueToday', 0),
                mastered=flashcard.get('mastered', 0),
                mastered_knowledge='、'.join(knowledge.get('mastered', [])[:5]) or '暂无',
                weak_areas='、'.join(knowledge.get('weakAreas', [])[:5]) or '暂无',
                interests='、'.join(knowledge.get('interests', [])[:5]) or '暂无',
                visual_vs_verbal=style.get('visual_vs_verbal', '未知'),
                active_vs_reflective=style.get('active_vs_reflective', '未知'),
                sensing_vs_intuitive=style.get('sensing_vs_intuitive', '未知'),
                sequential_vs_global=style.get('sequential_vs_global', '未知'),
            )

            # 调用LLM生成报告
            llm = get_simple_answer_llm()

            # 使用流式输出
            for chunk in llm.chat_stream([{"role": "user", "content": prompt}]):
                if chunk:
                    # SSE格式
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
            record_from_mimo(llm, 0, "analytics_report")

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"生成学习报告失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
