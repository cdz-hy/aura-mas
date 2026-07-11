"""
学习行为分析服务
定时分析用户学习行为，生成个性化策略
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.services.db.java_client import java_client
from app.agents.llm_factory import get_tutor_llm
from app.utils.profile_utils import ensure_learning_behavior_fields

logger = logging.getLogger("services.learning_analyzer")

# 分析任务配置
ANALYSIS_INTERVAL_HOURS = 5  # 每5小时分析一次
STRATEGY_EXPIRE_HOURS = 72   # 策略72小时过期


def _format_events_for_llm(events: List[Dict[str, Any]]) -> str:
    """将学习事件格式化为 LLM 可读的文本"""
    if not events:
        return "暂无学习行为数据"

    # 统计各类事件
    event_counts = {}
    total_study_seconds = 0
    quiz_scores = []
    resource_types = {}

    for event in events:
        event_type = event.get("eventType", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

        event_data = event.get("eventData", {})
        if isinstance(event_data, str):
            try:
                event_data = json.loads(event_data)
            except (json.JSONDecodeError, ValueError):
                event_data = {}

        # 统计学习时长
        if event_type == "page_view" and "duration" in event_data:
            total_study_seconds += event_data["duration"]

        # 统计测验成绩
        if event_type == "quiz_submit" and "score" in event_data:
            quiz_scores.append(event_data["score"])

        # 统计资源类型
        if event_type == "resource_complete" and "resourceType" in event_data:
            rt = event_data["resourceType"]
            resource_types[rt] = resource_types.get(rt, 0) + 1

    # 格式化输出
    lines = []
    lines.append(f"### 学习行为统计（最近{ANALYSIS_INTERVAL_HOURS}小时）")
    lines.append(f"- 总学习时长: {total_study_seconds // 60} 分钟")
    lines.append(f"- 事件分布: {json.dumps(event_counts, ensure_ascii=False)}")

    if quiz_scores:
        avg_score = sum(quiz_scores) / len(quiz_scores)
        lines.append(f"- 测验平均分: {avg_score:.1f}%")
        lines.append(f"- 测验次数: {len(quiz_scores)}")

    if resource_types:
        lines.append(f"- 完成资源类型: {json.dumps(resource_types, ensure_ascii=False)}")

    return "\n".join(lines)


async def analyze_user_behavior(user_id: int) -> Optional[Dict[str, Any]]:
    """
    分析用户学习行为并生成策略
    """
    try:
        # 1. 获取最近的学习事件（使用线程池避免阻塞）
        import asyncio
        events = await asyncio.to_thread(
            java_client._request, "GET", "/api/tracker/internal/events",
            params={"userId": user_id, "hours": ANALYSIS_INTERVAL_HOURS}
        )

        if not events or len(events) < 3:
            logger.info(f"[学习分析] 用户 {user_id} 事件不足，跳过分析")
            return None

        # 2. 获取用户画像（使用线程池避免阻塞）
        user_profile = await asyncio.to_thread(java_client.get_user_profile, user_id)
        if user_profile:
            user_profile = ensure_learning_behavior_fields(user_profile.get("learning_behavior", {}))
        else:
            user_profile = {}

        # 3. 获取学习计划（使用线程池避免阻塞）
        plans = await asyncio.to_thread(
            java_client._request, "GET", "/api/plan/list",
            params={"userId": user_id, "page": 1, "size": 10}
        )
        plan_list = plans.get("records", []) if isinstance(plans, dict) else []

        # 4. 格式化事件数据
        events_text = _format_events_for_llm(events)

        # 5. 构建分析提示词
        analysis_prompt = f"""你是一个专业的学习效果分析专家。请根据以下学生的学习行为数据，分析学习效果并生成个性化的学习策略建议。

## 学生学习行为数据
{events_text}

## 学生画像
- 知识基础: {user_profile.get('knowledge_base', [])}
- 薄弱点: {user_profile.get('weak_areas', [])}
- 兴趣标签: {user_profile.get('interest_tags', [])}
- 学习风格: visual_vs_verbal={user_profile.get('visual_vs_verbal', 0)}, active_vs_reflective={user_profile.get('active_vs_reflective', 0)}
- 目标导向: {user_profile.get('goal_orientation', 'exam')}

## 学习计划
{json.dumps(plan_list[:3], ensure_ascii=False) if plan_list else "暂无学习计划"}

## 请分析并输出 JSON
分析学生的学习效果，从以下维度评估：
1. 学习持续性（学习频率、时长规律）
2. 知识掌握度（测验正确率、进步趋势）
3. 学习效率（单位时间学习量）
4. 学习路径合理性（资源类型偏好、学习顺序）

并生成以下内容：

### 1. 策略建议（1-3条）
每条策略包含：
- strategy_type: resource_recommendation / plan_adjustment / review_schedule / learning_habit
- title: 策略标题（简洁）
- description: 策略描述（100字以内，亲切自然）
- data: 策略相关数据

### 2. 资源推送调整建议
根据学生的学习风格和薄弱点，推荐适合的资源类型：
- recommended_resource_types: 推荐的资源类型列表（如 ["quiz", "mindmap", "video"]）
- avoid_resource_types: 应避免的资源类型
- difficulty_adjustment: 难度调整建议（"easier" / "same" / "harder"）

### 3. 学习计划优化建议
根据学习进度和效果，提供计划调整建议：
- plan_adjustments: 计划调整建议列表
  - plan_id: 计划ID（如果有）
  - action: "accelerate" / "decelerate" / "reorder" / "add_review" / "skip" / "create_new"
  - reason: 调整原因
  - modules_to_adjust: 需要调整的模块列表
  - suggested_plan_focus: 如果是创建新计划，建议的学习主题
  - suggested_modules: 如果是创建新计划，建议的模块列表（每个模块包含 title 和 description）

**重要：suggested_modules 必须只包含与学习主题相关的知识性模块，不要包含"学习习惯"、"复习安排"、"综合应用"等非知识性内容。每个模块应该是一个具体的知识点或技能。**

输出格式：
{{
  "analysis": {{
    "continuity": 0.8,
    "mastery": 0.7,
    "efficiency": 0.6,
    "path合理性": 0.7,
    "overall_score": 0.7,
    "summary": "简要分析总结"
  }},
  "strategies": [...],
  "resource_recommendations": {{
    "recommended_resource_types": ["quiz", "mindmap"],
    "avoid_resource_types": ["video"],
    "difficulty_adjustment": "same",
    "reason": "推荐原因"
  }},
  "plan_adjustments": [
    {{
      "plan_id": null,
      "action": "create_new",
      "reason": "需要系统学习计算机网络基础",
      "modules_to_adjust": [],
      "suggested_plan_focus": "计算机网络基础",
      "suggested_modules": [
        {{"title": "OSI七层模型", "description": "理解网络分层架构"}},
        {{"title": "TCP/IP协议族", "description": "掌握核心协议"}}
      ]
    }}
  ]
}}
}}"""

        # 6. 调用 LLM 分析（使用线程池避免阻塞）
        llm = get_tutor_llm()
        messages = [
            {"role": "system", "content": "你是一个专业的学习效果分析专家，善于从学习行为数据中发现问题并给出个性化建议。"},
            {"role": "user", "content": analysis_prompt}
        ]

        result = await asyncio.to_thread(llm.chat_json, messages)

        # 检查 LLM 返回结果
        if not result or not isinstance(result, dict):
            logger.warning(f"[学习分析] 用户 {user_id} LLM 返回无效结果: {result}")
            return None

        analysis = result.get("analysis", {})
        summary = analysis.get("summary", "") if isinstance(analysis, dict) else ""
        logger.info(f"[学习分析] 用户 {user_id} 分析完成: {summary[:50]}")

        return result

    except Exception as e:
        logger.error(f"[学习分析] 用户 {user_id} 分析失败: {e}", exc_info=True)
        return None


async def save_strategies(user_id: int, analysis_result: Dict[str, Any]):
    """将分析结果保存为策略"""
    import asyncio
    try:
        strategies = analysis_result.get("strategies", [])
        for strategy in strategies:
            strategy_type = strategy.get("strategy_type", "general")
            title = strategy.get("title", "学习建议")
            description = strategy.get("description", "")
            data = strategy.get("data", {})

            # 包含分析结果
            data["analysis"] = analysis_result.get("analysis", {})

            await asyncio.to_thread(
                java_client._request, "POST", "/api/tracker/internal/strategies",
                params={
                    "userId": user_id,
                    "strategyType": strategy_type,
                    "title": title,
                    "description": description,
                    "expireHours": STRATEGY_EXPIRE_HOURS
                },
                json=data
            )

        # 保存资源推荐策略
        resource_recs = analysis_result.get("resource_recommendations")
        if resource_recs:
            await asyncio.to_thread(
                java_client._request, "POST", "/api/tracker/internal/strategies",
                params={
                    "userId": user_id,
                    "strategyType": "resource_recommendation",
                    "title": "个性化资源推荐",
                    "description": f"根据你的学习风格，推荐使用 {', '.join(resource_recs.get('recommended_resource_types', []))} 类型的资源",
                    "expireHours": STRATEGY_EXPIRE_HOURS
                },
                json={
                    "analysis": analysis_result.get("analysis", {}),
                    "recommendations": resource_recs
                }
            )

        # 保存计划调整策略
        plan_adjustments = analysis_result.get("plan_adjustments", [])
        for adjustment in plan_adjustments:
            action = adjustment.get("action", "")
            reason = adjustment.get("reason", "")
            modules = adjustment.get("modules_to_adjust", [])
            plan_id = adjustment.get("plan_id")
            suggested_focus = adjustment.get("suggested_plan_focus", "")
            suggested_modules = adjustment.get("suggested_modules", [])

            action_labels = {
                "accelerate": "加速学习",
                "decelerate": "放慢节奏",
                "reorder": "调整顺序",
                "add_review": "增加复习",
                "skip": "跳过内容",
                "create_new": "创建新计划"
            }
            action_label = action_labels.get(action, "调整计划")

            # 构建描述
            description = reason
            if suggested_focus:
                description = f"建议创建「{suggested_focus}」学习计划：{reason}"

            # 保存策略
            await asyncio.to_thread(
                java_client._request, "POST", "/api/tracker/internal/strategies",
                params={
                    "userId": user_id,
                    "strategyType": "plan_adjustment",
                    "title": f"计划建议：{action_label}" if action == "create_new" else f"计划调整建议：{action_label}",
                    "description": description,
                    "expireHours": STRATEGY_EXPIRE_HOURS
                },
                json={
                    "analysis": analysis_result.get("analysis", {}),
                    "adjustment": adjustment,
                    "suggested_plan_focus": suggested_focus,
                    "suggested_modules": suggested_modules
                }
            )

            # 如果有具体的计划ID，执行调整
            if plan_id and action:
                try:
                    await asyncio.to_thread(
                        java_client.adjust_plan,
                        plan_id=plan_id,
                        action=action,
                        reason=reason,
                        modules=modules
                    )
                    logger.info(f"[学习分析] 用户 {user_id} 计划 {plan_id} 调整执行: {action}")
                except Exception as e:
                    logger.warning(f"[学习分析] 用户 {user_id} 计划 {plan_id} 调整失败: {e}")

        total_count = len(strategies) + (1 if resource_recs else 0) + len(plan_adjustments)
        logger.info(f"[学习分析] 用户 {user_id} 保存 {total_count} 条策略")

    except Exception as e:
        logger.error(f"[学习分析] 用户 {user_id} 保存策略失败: {e}", exc_info=True)


async def run_analysis_for_user(user_id: int):
    """为单个用户运行分析"""
    logger.info(f"[学习分析] 开始分析用户 {user_id}")
    result = await analyze_user_behavior(user_id)
    if result and result.get("strategies"):
        await save_strategies(user_id, result)
    logger.info(f"[学习分析] 用户 {user_id} 分析完成")


async def run_analysis_for_all_users():
    """为所有活跃用户运行分析"""
    import asyncio
    try:
        # 获取最近5小时有学习事件的活跃用户（使用线程池避免阻塞）
        active_user_ids = await asyncio.to_thread(
            java_client._request, "GET", "/api/tracker/internal/active-users",
            params={"hours": ANALYSIS_INTERVAL_HOURS}
        )

        if not active_user_ids or not isinstance(active_user_ids, list):
            logger.info("[学习分析] 没有活跃用户需要分析")
            return

        logger.info(f"[学习分析] 开始批量分析, 活跃用户数: {len(active_user_ids)}")

        success_count = 0
        fail_count = 0

        for user_id in active_user_ids:
            try:
                await run_analysis_for_user(user_id)
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"[学习分析] 用户 {user_id} 分析失败: {e}")

        logger.info(f"[学习分析] 批量分析完成, 成功: {success_count}, 失败: {fail_count}")

    except Exception as e:
        logger.error(f"[学习分析] 批量分析失败: {e}", exc_info=True)
