"""
学习分析 API - AI学习报告生成 + 首页个性化问候
"""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.llm_factory import get_simple_answer_llm
from app.services.db.java_client import java_client
from app.services.cache import _get_redis
from app.utils.token_recorder import record_from_mimo
from app.prompts.plan_icon_prompt import ICON_LIBRARY, get_system_prompt, get_icon_svg

logger = logging.getLogger(__name__)
router = APIRouter()

# 首页问候语缓存 TTL（3分钟）
GREETING_TTL = 180


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


# ==================== 首页个性化问候语 ====================

GREETING_PROMPT = """你是一个温暖的学习助手。根据用户的学习数据，生成一句简短的个性化问候语。

## 用户学习数据
- 当前时间: {time_of_day}
- 学习计划数: {total_plans}个（进行中{active_plans}个，已完成{completed_plans}个）
- 今日学习时长: {today_minutes}分钟
- 累计学习时长: {total_hours}小时
- 连续学习天数: {streak}天
- 待复习闪卡: {due_cards}张
- 最近学习内容: {recent_topics}

## 要求
- 20-35字，简洁温暖
- 根据数据动态生成，不要每次都一样
- 语气像朋友打招呼，自然亲切
- 可以适当鼓励或提醒
- 不要用emoji
- 直接输出问候语，不要添加引号或额外解释"""


@router.get("/greeting")
async def get_greeting(user_id: int):
    """获取首页个性化问候语（带3分钟Redis缓存）"""
    try:
        # 1. 尝试从缓存获取
        redis = _get_redis()
        cache_key = f"aura:greeting:{user_id}"
        if redis:
            try:
                cached = redis.get(cache_key)
                if cached:
                    return {"greeting": cached}
            except Exception as e:
                logger.warning(f"读取问候语缓存失败: {e}")

        # 2. 缓存未命中，获取用户数据
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 6:
            time_of_day = "深夜"
        elif hour < 12:
            time_of_day = "上午"
        elif hour < 14:
            time_of_day = "中午"
        elif hour < 18:
            time_of_day = "下午"
        else:
            time_of_day = "晚上"

        # 获取用户画像和学习数据
        profile = {}
        try:
            profile = java_client.get_user_profile(user_id)
        except Exception:
            pass

        # 从画像中提取学习数据
        behavior = profile.get("learning_behavior", {})
        if isinstance(behavior, str):
            try:
                behavior = json.loads(behavior)
            except Exception:
                behavior = {}

        # 优先从 Java 后端获取实时、真实的学习统计数据
        try:
            headers = {"X-User-Id": str(user_id)}
            # 1) 获取仪表盘统计数据 (包含学习时长、计划完成情况等)
            dashboard_stats = java_client._request("GET", "/api/stats/dashboard", headers=headers) or {}
            # 2) 获取学习热力图数据 (包含当前连续学习天数)
            heatmap_stats = java_client._request("GET", "/api/stats/study-heatmap", headers=headers) or {}
            # 3) 获取闪卡统计数据 (包含今日待复习数)
            flashcard_stats = java_client._request("GET", "/api/stats/flashcard-stats", headers=headers) or {}

            total_plans = dashboard_stats.get("totalPlans", 0)
            active_plans = dashboard_stats.get("activePlans", 0)
            completed_plans = dashboard_stats.get("completedPlans", 0)
            today_minutes = dashboard_stats.get("todayDurationSeconds", 0) // 60
            total_hours = dashboard_stats.get("totalStudyHours", 0)
            streak = heatmap_stats.get("currentStreak", 0)
            due_cards = flashcard_stats.get("dueToday", 0)
            logger.info(f"成功获取用户 {user_id} 实时数据: plans={total_plans}(active={active_plans}), today={today_minutes}m, hours={total_hours}h, streak={streak}d, cards={due_cards}")
        except Exception as e:
            logger.warning(f"获取 Java 实时统计失败，采用画像估算兜底: {e}")
            # 兜底降级估算逻辑
            total_plans = len(behavior.get("knowledge_base", [])) + 2  # 估算
            active_plans = max(1, total_plans // 2)
            completed_plans = max(0, total_plans - active_plans)
            today_minutes = 0
            total_hours = behavior.get("study_hours", 0)
            streak = behavior.get("streak_days", 0)
            due_cards = behavior.get("due_cards", 0)

        recent_topics = "、".join(behavior.get("interest_tags", [])[:3]) or "暂无"

        # 3. 调用LLM生成问候语
        prompt = GREETING_PROMPT.format(
            time_of_day=time_of_day,
            total_plans=total_plans,
            active_plans=active_plans,
            completed_plans=completed_plans,
            today_minutes=today_minutes,
            total_hours=total_hours,
            streak=streak,
            due_cards=due_cards,
            recent_topics=recent_topics,
        )

        llm = get_simple_answer_llm()
        greeting = ""
        for chunk in llm.chat_stream([{"role": "user", "content": prompt}]):
            if chunk:
                greeting += chunk
        record_from_mimo(llm, user_id, "greeting")

        greeting = greeting.strip().strip('"').strip("'")

        # 4. 写入缓存
        if redis and greeting:
            try:
                redis.setex(cache_key, GREETING_TTL, greeting)
            except Exception as e:
                logger.warning(f"写入问候语缓存失败: {e}")

        return {"greeting": greeting}

    except Exception as e:
        logger.error(f"生成问候语失败: {e}")
        # 降级返回默认问候语
        return {"greeting": "继续你的学习之旅"}


# ==================== 计划SVG图标生成（选择模式） ====================


@router.post("/plan-icon")
async def generate_plan_icon(request: dict):
    """
    生成计划SVG图标并直接更新Java后端
    采用"选择"模式：从预定义图标库中选择最合适的图标
    """
    try:
        plan_id = request.get("plan_id")
        plan_title = request.get("plan_title", "")
        resource_titles = request.get("resource_titles", [])

        if not plan_title:
            return {"svg": None, "error": "缺少计划标题"}

        # 构建用户提示词
        resources_text = "、".join(resource_titles[:5]) if resource_titles else "无"
        user_prompt = f"""请为以下学习计划选择最合适的图标：

计划名称：{plan_title}
关联学习资源主题：{resources_text}

请分析计划主题，从图标库中选择 1 个最契合的图标。"""

        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]

        # 调用 LLM 选择图标（温度 0.0，确保稳定输出）
        llm = get_simple_answer_llm()
        result = llm.chat_json(messages, temperature=0.0, max_tokens=1024)
        record_from_mimo(llm, 0, "plan_icon_generation")

        # 解析结果
        icon_key = result.get("icon_key", "")
        description = result.get("description", plan_title)

        # 验证 icon_key 有效性
        if not icon_key or icon_key not in ICON_LIBRARY:
            logger.warning(f"LLM 返回的 icon_key 无效: {icon_key}，使用默认值")
            icon_key = _infer_icon_key(plan_title, resource_titles)

        # 使用预定义图标库生成 SVG（保证质量）
        svg = get_icon_svg(icon_key)
        logger.info(f"[计划图标] 为计划 '{plan_title}' 选择了图标: {icon_key}, 描述: {description}")

        # 直接更新Java后端的planConfig（使用内部API）
        if plan_id:
            try:
                # 先获取当前的planConfig
                plan_data = java_client.get_plan(int(plan_id))
                existing_config = {}
                if plan_data:
                    raw_config = plan_data.get("planConfig")
                    if raw_config:
                        if isinstance(raw_config, str):
                            existing_config = json.loads(raw_config)
                        elif isinstance(raw_config, dict):
                            existing_config = raw_config

                # 更新图标字段
                existing_config["iconSvg"] = svg
                existing_config["iconDescription"] = description
                existing_config["iconKey"] = icon_key

                # 调用Java内部API更新（无需用户认证）
                java_client._request("PUT", f"/api/plan/internal/{plan_id}/config", json={
                    "planConfig": existing_config
                })
                logger.info(f"[计划图标] 已更新计划 {plan_id} 的图标配置")
            except Exception as e:
                logger.warning(f"[计划图标] 更新Java后端失败: {e}")

        return {"svg": svg, "description": description}

    except Exception as e:
        logger.error(f"生成计划图标失败: {e}")
        return {"svg": None, "error": str(e)}


def _infer_icon_key(plan_title: str, resource_titles: list[str]) -> str:
    """
    根据计划标题和资源标题智能推断图标 key
    作为 LLM 选择失败时的兜底逻辑
    """
    title_lower = plan_title.lower()
    resource_text = " ".join(resource_titles).lower() if resource_titles else ""
    full_text = f"{title_lower} {resource_text}"

    # 关键词匹配规则
    keyword_rules = [
        (["python", "爬虫", "自动化"], "python"),
        (["java", "spring", "jvm"], "java"),
        (["前端", "vue", "react", "angular", "html", "css", "javascript", "typescript"], "web"),
        (["数据库", "sql", "mysql", "postgresql", "mongodb", "redis"], "database"),
        (["ai", "人工智能", "机器学习", "深度学习", "神经网络", "大模型", "llm", "gpt", "transformer"], "brain"),
        (["算法", "数据结构", "排序", "搜索", "动态规划"], "algorithm"),
        (["api", "接口", "微服务", "restful"], "api"),
        (["数据分析", "统计", "可视化", "图表", "dashboard"], "chart"),
        (["linux", "运维", "部署", "docker", "kubernetes", "服务器"], "server"),
        (["安全", "加密", "认证", "security"], "lock"),
        (["云计算", "云", "aws", "azure"], "cloud"),
        (["数学", "线性代数", "概率", "微积分"], "math"),
        (["设计", "架构", "模式", "分层"], "layers"),
        (["入门", "基础", "学习", "教程", "课程"], "book"),
        (["实战", "项目", "开发"], "rocket"),
        (["终端", "命令行", "shell", "bash"], "terminal"),
        (["代码", "编程", "程序", "coding"], "code"),
    ]

    for keywords, key in keyword_rules:
        for kw in keywords:
            if kw in full_text:
                return key

    # 默认返回书本图标
    return "book"
