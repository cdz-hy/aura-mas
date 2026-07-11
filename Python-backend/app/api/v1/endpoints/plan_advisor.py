"""
AI 学习顾问 API
提供智能对话、学习分析、计划建议、语音合成等功能

前端调用:
  POST /api/ai/plan-advisor/chat
  POST /api/ai/plan-advisor/tts
"""
import json
import logging
import base64
import requests as http_requests
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.agents.llm_factory import get_tutor_llm
from app.services.db.java_client import java_client
from app.utils.profile_utils import ensure_learning_behavior_fields, update_learning_behavior
from app.core.config import settings

logger = logging.getLogger("api.plan_advisor")
router = APIRouter()


class AdvisorRequest(BaseModel):
    """学习顾问请求"""
    stats: Optional[Dict[str, Any]] = None
    plans: Optional[List[Dict[str, Any]]] = None
    userMessage: str = ""


# 系统提示词
ADVISOR_SYSTEM_PROMPT = """你是一个温暖、专业的 AI 学习顾问。你的职责是：

1. **主动分析**：仔细阅读学生的学习计划和资源内容，了解学生在学什么、学到什么程度
2. **主动关怀**：发现学生学习中的问题，主动提供帮助和建议
3. **主动追问**：根据学习计划和资源内容，主动提出有针对性的问题
4. **计划建议**：根据学生的学习情况和需求，推荐合适的新学习计划

## 主动行为指南
- **不要等学生来问**，你要主动发现问题并提出
- **基于学习计划内容**：仔细分析学生的计划和资源，看看有没有需要补充的地方
- **基于学习进度**：如果某个计划很久没更新，可以主动询问
- **基于薄弱点**：如果发现学生有薄弱领域，主动建议加强
- **鼓励与引导**：如果学生学习情况良好，给予鼓励并引导深入学习

## 语言风格
- 像朋友一样聊天，不要太正式
- 关心学生的学习状态，适时鼓励
- 回答简洁明了，控制在 200 字以内
- 使用中文回复
- 不要使用 emoji

## 输出格式
严格输出 JSON：
{
  "message": "你的回复/提问/建议内容",
  "profile_update": {
    "should_update": true/false,
    "updates": {
      "visual_vs_verbal": 增量值或null,
      "active_vs_reflective": 增量值或null,
      "sensing_vs_intuitive": 增量值或null,
      "sequential_vs_global": 增量值或null
    }
  },
  "plan_suggestion": {
    "should_suggest": true/false,
    "title": "建议的计划标题",
    "description": "计划描述",
    "modules": [
      {"title": "模块标题", "description": "模块描述"}
    ]
  }
}

## 注意
- profile_update 中的 updates 是增量值（如 +0.1 或 -0.1）
- plan_suggestion 只有在真正需要新计划时才生成（比如学生计划不足、内容不全面、需要补充某个领域）
- 如果学生的学习计划已经足够且进展正常，plan_suggestion.should_suggest 设为 false
- 当学生消息包含"[系统自动触发]"时，表示这是系统主动发起的对话，你要主动分析并提出问题或建议
"""


def _format_stats(stats: Dict[str, Any]) -> str:
    """格式化学习统计数据"""
    if not stats:
        return "暂无学习数据"

    lines = []
    if "todayStudyMinutes" in stats:
        minutes = stats["todayStudyMinutes"]
        if minutes >= 60:
            lines.append(f"今日学习: {minutes // 60}小时{minutes % 60}分钟")
        else:
            lines.append(f"今日学习: {minutes}分钟")

    if "streakDays" in stats:
        lines.append(f"连续学习: {stats['streakDays']}天")

    if "totalStudyMinutes" in stats:
        minutes = stats["totalStudyMinutes"]
        if minutes >= 60:
            lines.append(f"总学习时长: {minutes // 60}小时{minutes % 60}分钟")
        else:
            lines.append(f"总学习时长: {minutes}分钟")

    if "quizAccuracy" in stats:
        lines.append(f"答题正确率: {stats['quizAccuracy']}%")

    if "completedModules" in stats and "totalModules" in stats:
        lines.append(f"完成模块: {stats['completedModules']}/{stats['totalModules']}")

    return "\n".join(lines) if lines else "暂无学习数据"


def _format_plans(plans: List[Dict[str, Any]]) -> str:
    """格式化学习计划列表"""
    if not plans:
        return "暂无学习计划"

    lines = []
    for i, plan in enumerate(plans[:5], 1):
        title = plan.get("title", "未命名计划")
        status = plan.get("status", 0)
        status_text = {0: "未开始", 1: "进行中", 2: "学习中", 3: "暂停", 4: "已完成"}.get(status, "未知")
        lines.append(f"{i}. {title} ({status_text})")

    return "\n".join(lines)


@router.post("/chat")
async def advisor_chat(
    request: AdvisorRequest,
    authorization: Optional[str] = Header(None),
):
    """
    AI 学习顾问对话
    """
    # 验证 ticket
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证信息")

    ticket = authorization.replace("Bearer ", "")
    try:
        ticket_info = java_client.validate_ticket(ticket)
        user_id = ticket_info["user_id"]
    except Exception as e:
        logger.error(f"Ticket 验证失败: {e}")
        raise HTTPException(status_code=401, detail="认证失败")

    logger.info(f"[AI顾问] 用户 {user_id}, 消息: {request.userMessage[:50]}")

    # 获取用户画像
    user_profile = {}
    try:
        user_profile = java_client.get_user_profile(user_id)
        user_profile = ensure_learning_behavior_fields(user_profile.get("learning_behavior", {}))
    except Exception:
        pass

    # 获取用户的学习计划详情和资源内容
    plans_with_resources = []
    if request.plans:
        for plan in request.plans[:3]:  # 只取前3个计划
            plan_id = plan.get("id")
            if plan_id:
                try:
                    # 获取计划的资源列表
                    resources = java_client.get_plan_resources(plan_id)
                    # 处理资源数据，解析 moduleData
                    processed_resources = []
                    if resources:
                        for res in resources[:5]:  # 每个计划最多5个资源
                            module_data = res.get('moduleData', {})
                            if isinstance(module_data, str):
                                try:
                                    module_data = json.loads(module_data)
                                except:
                                    module_data = {}
                            title = res.get('title') or module_data.get('title', '未命名')
                            # 获取资源内容摘要
                            content = module_data.get('content', '')
                            content_summary = content[:200] + '...' if len(content) > 200 else content
                            processed_resources.append({
                                "id": res.get("id"),
                                "moduleType": res.get("moduleType", "text"),
                                "title": title,
                                "status": res.get("status", 0),
                                "content_summary": content_summary,
                            })
                    plans_with_resources.append({
                        "id": plan_id,
                        "title": plan.get("title", ""),
                        "status": plan.get("status", 0),
                        "resources": processed_resources
                    })
                except Exception as e:
                    logger.warning(f"[AI顾问] 获取计划 {plan_id} 资源失败: {e}")
                    plans_with_resources.append({
                        "id": plan_id,
                        "title": plan.get("title", ""),
                        "status": plan.get("status", 0),
                        "resources": []
                    })

    # 构造上下文
    stats_text = _format_stats(request.stats) if request.stats else "暂无学习数据"
    plans_text = _format_plans(request.plans) if request.plans else "暂无学习计划"

    # 构造详细的计划和资源信息
    plans_detail_text = ""
    if plans_with_resources:
        for i, plan in enumerate(plans_with_resources, 1):
            plans_detail_text += f"\n### 计划{i}: {plan['title']}\n"
            if plan['resources']:
                for j, res in enumerate(plan['resources'][:5], 1):
                    title = res.get('title', '未命名')
                    module_type = res.get('moduleType', 'text')
                    status = res.get('status', 0)
                    status_text = {0: "未开始", 1: "学习中", 2: "已完成"}.get(status, "未知")
                    content_summary = res.get('content_summary', '')
                    plans_detail_text += f"  {j}. [{module_type}] {title} ({status_text})\n"
                    if content_summary:
                        plans_detail_text += f"     内容摘要: {content_summary}\n"
            else:
                plans_detail_text += "  暂无资源\n"

    # 构造用户输入
    user_input = f"""## 学生的学习数据
{stats_text}

## 学生的学习计划详情（包含资源内容）
{plans_detail_text if plans_detail_text else "暂无学习计划"}

## 学生的画像
- 知识基础: {user_profile.get('knowledge_base', [])}
- 薄弱点: {user_profile.get('weak_areas', [])}
- 兴趣标签: {user_profile.get('interest_tags', [])}
- 学习风格: visual_vs_verbal={user_profile.get('visual_vs_verbal', 0)}, active_vs_reflective={user_profile.get('active_vs_reflective', 0)}

## 学生的问题
{request.userMessage}

## 你的任务
1. **分析学生的学习计划和资源内容**：仔细阅读上面的学习计划详情，了解学生在学什么、学到了什么程度
2. **基于计划内容回复**：根据学生具体的计划和资源来回答问题，而不是只看统计数据
3. **判断是否需要新计划**：
   - 如果学生已有足够计划且内容覆盖全面，不需要建议新计划
   - 如果计划太少、内容不全面、或需要补充某个领域，才提供建议
4. **建议新计划时**：要基于学生已有的学习内容，避免重复，针对薄弱点

请根据以上信息回复学生，并输出 JSON:"""

    # 保存用户消息到数据库
    session_id = f"advisor-{user_id}"
    logger.info(f"[AI顾问] 保存用户消息: session_id={session_id}, message={request.userMessage[:50]}")
    try:
        result = java_client.create_dialogue(
            user_id=user_id,
            session_id=session_id,
            conversation_text=request.userMessage,
            dialogue_type="USER",
            intent_type="plan_advisor",
        )
        logger.info(f"[AI顾问] 用户消息保存成功: {result}")
    except Exception as e:
        logger.error(f"[AI顾问] 保存用户消息失败: {e}", exc_info=True)

    # 调用 LLM
    llm = get_tutor_llm()
    messages = [
        {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    try:
        result = llm.chat_json(messages)
    except Exception as e:
        logger.error(f"[AI顾问] LLM 调用失败: {e}")
        return JSONResponse(content={
            "message": "抱歉，处理你的请求时出现了问题。请稍后再试。",
            "type": "text"
        })

    # 处理响应
    message = result.get("message", "抱歉，我没有理解你的问题。")
    profile_update = result.get("profile_update", {})
    plan_suggestion = result.get("plan_suggestion", {})

    # 保存 AI 回复到数据库
    logger.info(f"[AI顾问] 保存AI回复: session_id={session_id}, message={message[:50]}")
    try:
        result = java_client.create_dialogue(
            user_id=user_id,
            session_id=session_id,
            conversation_text=message,
            dialogue_type="AI",
            intent_type="plan_advisor",
        )
        logger.info(f"[AI顾问] AI回复保存成功: {result}")
    except Exception as e:
        logger.error(f"[AI顾问] 保存AI回复失败: {e}", exc_info=True)

    # 更新画像
    if profile_update.get("should_update") and profile_update.get("updates"):
        try:
            updates = profile_update["updates"]
            current_behavior = ensure_learning_behavior_fields(user_profile)
            updated_behavior = update_learning_behavior(
                current=current_behavior,
                updates=updates,
                confidence=0.6,
            )
            java_client.save_user_profile(user_id, updated_behavior, "AI顾问对话自动更新")
            logger.info(f"[AI顾问] 画像更新成功")
        except Exception as e:
            logger.warning(f"[AI顾问] 画像更新失败: {e}")

    # 返回响应
    if plan_suggestion.get("should_suggest") and plan_suggestion.get("modules"):
        return JSONResponse(content={
            "message": message,
            "type": "plan_suggestion",
            "suggestion": {
                "title": plan_suggestion.get("title", "推荐学习计划"),
                "description": plan_suggestion.get("description", ""),
                "modules": plan_suggestion.get("modules", [])
            }
        })

    return JSONResponse(content={
        "message": message,
        "type": "text"
    })


class CreatePlanRequest(BaseModel):
    """创建计划请求"""
    title: str
    description: str = ""
    modules: List[Dict[str, Any]] = []


@router.post("/create-plan")
async def create_plan_from_suggestion(
    request: CreatePlanRequest,
    authorization: Optional[str] = Header(None),
):
    """
    根据建议创建学习计划
    """
    # 验证 ticket
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证信息")

    ticket = authorization.replace("Bearer ", "")
    try:
        ticket_info = java_client.validate_ticket(ticket)
        user_id = ticket_info["user_id"]
    except Exception as e:
        logger.error(f"Ticket 验证失败: {e}")
        raise HTTPException(status_code=401, detail="认证失败")

    logger.info(f"[AI顾问] 用户 {user_id} 创建计划: {request.title}")

    try:
        # 1. 创建学习计划
        logger.info(f"[AI顾问] 调用 create_plan: user_id={user_id}, title={request.title}")

        # learning_goal 需要 JSON 格式
        learning_goal = json.dumps({
            "goal": request.description or request.title,
            "source": "ai_advisor",
            "modules_count": len(request.modules)
        }, ensure_ascii=False)

        plan_result = java_client.create_plan(
            user_id=user_id,
            title=request.title,
            learning_goal=learning_goal,
            status=0,
        )
        logger.info(f"[AI顾问] create_plan 返回: {plan_result}")

        plan_id = plan_result.get("id") if isinstance(plan_result, dict) else None
        if not plan_id:
            logger.error(f"[AI顾问] 创建计划失败，返回数据: {plan_result}")
            raise HTTPException(status_code=500, detail=f"创建计划失败: {plan_result}")

        logger.info(f"[AI顾问] 计划创建成功，ID: {plan_id}")

        # 2. 为每个模块创建资源占位
        resource_ids = []
        for i, module in enumerate(request.modules, 1):
            module_title = module.get("title", f"模块{i}")
            module_description = module.get("description", "")

            try:
                resource_result = java_client.create_resource(
                    plan_id=plan_id,
                    module_type="text",
                    module_data={
                        "title": module_title,
                        "description": module_description,
                    },
                    module_order=i,
                    status=0,  # 未开始
                )
                resource_id = resource_result.get("id")
                if resource_id:
                    resource_ids.append(resource_id)
                    logger.info(f"[AI顾问] 资源创建成功，ID: {resource_id}, 标题: {module_title}")
            except Exception as e:
                logger.warning(f"[AI顾问] 创建资源失败: {e}")

        # 3. 返回创建结果，让前端触发资源生成
        logger.info(f"[AI顾问] 计划创建完成，共 {len(resource_ids)} 个资源")

        # 3. 保存顾问对话记录
        session_id = f"advisor-{user_id}"
        try:
            java_client.create_dialogue(
                user_id=user_id,
                session_id=session_id,
                conversation_text=f"[系统] 已根据建议创建学习计划「{request.title}」，包含 {len(resource_ids)} 个模块",
                dialogue_type="AI",
                intent_type="plan_advisor",
            )
        except Exception as e:
            logger.warning(f"[AI顾问] 保存对话记录失败: {e}")

        return JSONResponse(content={
            "success": True,
            "planId": plan_id,
            "resourceIds": resource_ids,
            "message": f"已成功创建学习计划「{request.title}」，包含 {len(resource_ids)} 个模块"
        })

    except Exception as e:
        logger.error(f"[AI顾问] 创建计划失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建计划失败: {str(e)}")


class TTSRequest(BaseModel):
    """语音合成请求"""
    text: str
    voice: str = "冰糖"


@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    authorization: Optional[str] = Header(None),
):
    """
    语音合成 - 使用 MiMo TTS API
    返回 WAV 音频数据
    """
    # 验证 ticket
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证信息")

    ticket = authorization.replace("Bearer ", "")
    try:
        ticket_info = java_client.validate_ticket(ticket)
        user_id = ticket_info["user_id"]
    except Exception as e:
        logger.error(f"Ticket 验证失败: {e}")
        raise HTTPException(status_code=401, detail="认证失败")

    logger.info(f"[TTS] 用户 {user_id}, 文本长度: {len(request.text)}, 音色: {request.voice}")

    try:
        # 调用 MiMo TTS API
        url = f"{settings.MIMO_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.MIMO_API_KEY}"
        }
        payload = {
            "model": "mimo-v2.5-tts",
            "messages": [
                {
                    "role": "user",
                    "content": "用温馨、自然、清晰的中文播报音色"
                },
                {
                    "role": "assistant",
                    "content": request.text
                }
            ],
            "audio": {
                "format": "wav",
                "voice": request.voice
            }
        }

        resp = http_requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            logger.error(f"[TTS] MiMo TTS API 调用失败: {resp.status_code} - {resp.text}")
            raise HTTPException(status_code=500, detail="语音合成失败")

        result = resp.json()
        choices = result.get("choices", [])
        if not choices:
            raise HTTPException(status_code=500, detail="语音合成返回空结果")

        audio_data = choices[0].get("message", {}).get("audio", {}).get("data")
        if not audio_data:
            raise HTTPException(status_code=500, detail="语音合成未返回音频数据")

        # 解码 base64 音频数据
        audio_bytes = base64.b64decode(audio_data)

        logger.info(f"[TTS] 语音合成成功, 音频大小: {len(audio_bytes)} 字节")

        # 返回 WAV 音频
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TTS] 语音合成异常: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")
