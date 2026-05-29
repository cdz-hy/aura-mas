"""
MQ 任务消费者 - 接收 Java 分发的资源生成任务
流程：MQ 收到任务 → 查询上下文 → LangGraph 工作流 → HTTP 持久化到 Java 后端（内部触发 SSE 推送）
"""
import asyncio
import json
import logging
from typing import Optional
import aio_pika
from app.core.config import settings
from app.graph.learning_graph import get_learning_graph
from app.agents.schemas import AgentState, NODE_ANIMATION_SKILL_GENERATOR
from app.services.db.java_client import java_client

logger = logging.getLogger("mq.consumer")


def _parse_module_data(raw) -> dict:
    """兼容 Java 返回的 moduleData 字符串/对象。"""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {"content": raw}
    return raw if isinstance(raw, dict) else {}


def _extract_resource_context(resource_info: dict) -> tuple[str, str, str, int]:
    md = _parse_module_data(resource_info.get("moduleData") if isinstance(resource_info, dict) else None)
    module_title = md.get("module_title") or md.get("title", "")
    resource_desc = md.get("module_description") or md.get("description", "")
    source_resource_content = md.get("content") or md.get("html") or ""
    current_module_order = resource_info.get("moduleOrder", 0) if isinstance(resource_info, dict) else 0
    return module_title, resource_desc, source_resource_content, current_module_order


def _resolve_source_resource_content(plan_id: int, current_module_order: int, current_resource_id: int) -> str:
    """动画占位资源内容为空时，回到同一模块找已生成正文资源作为动画源。"""
    if not current_module_order:
        return ""

    try:
        resources = java_client.get_resources_by_module(plan_id, current_module_order)
    except Exception as e:
        logger.warning("  [MQ 消费] 获取同模块资源失败: %s", e)
        return ""

    preferred_types = ("text", "document", "reading", "summary", "code")
    for preferred in preferred_types:
        for resource in resources or []:
            if resource.get("id") == current_resource_id:
                continue
            if resource.get("status") != 2 or resource.get("moduleType") != preferred:
                continue
            md = _parse_module_data(resource.get("moduleData"))
            content = md.get("content") or md.get("summary") or ""
            if content:
                logger.info("  [MQ 消费] 动画源内容来自同模块 %s 资源: id=%s, 长度=%d",
                            preferred, resource.get("id"), len(content))
                return content

    return ""


class MQConsumer:
    """监听 ai.resource.generation 队列，消费资源生成任务"""

    EXCHANGE = "ai.exchange"
    QUEUE_GENERATION = "ai.resource.generation"
    ROUTING_KEY_GENERATION = "ai.resource.generation"

    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
        self._consumer_tag: Optional[str] = None
        self._running = False

    async def start(self):
        """启动 MQ 消费者（阻塞直到连接就绪或失败）"""
        try:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=1)

            queue = await self._channel.declare_queue(
                self.QUEUE_GENERATION, durable=True
            )
            self._consumer_tag = await queue.consume(self._on_task)
            self._running = True
            logger.info("MQ 消费者已启动，监听队列: %s", self.QUEUE_GENERATION)
        except Exception as e:
            logger.warning("MQ 消费者启动失败（MQ 可能未就绪）: %s", e)
            self._running = False

    async def stop(self):
        """停止消费者"""
        self._running = False
        if self._consumer_tag and self._channel:
            await self._channel.cancel(self._consumer_tag)
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("MQ 消费者已停止")

    @property
    def running(self) -> bool:
        return self._running

    async def _on_task(self, message: aio_pika.IncomingMessage):
        """收到资源生成任务后的处理入口"""
        async with message.process():
            try:
                body = json.loads(message.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.error(
                    "MQ 消息解析失败，已丢弃非 JSON 消息: %s, body_prefix=%s",
                    e,
                    message.body[:16].hex(),
                )
                return

            task_id = body.get("taskId")
            plan_id = body.get("planId")
            resource_id = body.get("resourceId")
            user_id = body.get("userId")
            agent_chain = body.get("agentChain")

            logger.info("─" * 60)
            logger.info("  [MQ 消费] 收到资源生成任务")
            logger.info("    taskId=%s, planId=%s, resourceId=%s, userId=%s",
                        task_id, plan_id, resource_id, user_id)
            logger.info("─" * 60)

            if not all([task_id, plan_id, resource_id, user_id]):
                logger.error("MQ 消息缺少必要字段，忽略")
                return

            try:
                await self._process_task(
                    task_id=int(task_id),
                    plan_id=int(plan_id),
                    resource_id=int(resource_id),
                    user_id=int(user_id),
                    agent_chain=agent_chain,
                )
            except Exception as e:
                logger.error("任务处理异常: %s", e, exc_info=True)
                await self._fail_task(int(task_id), int(user_id), str(e))

    async def _process_task(
        self, task_id: int, plan_id: int, resource_id: int,
        user_id: int, agent_chain: Optional[str] = None,
    ):
        """执行资源生成核心逻辑"""
        # 1. 获取上下文数据（计划、资源、用户画像）
        plan_info = java_client.get_plan(plan_id)
        resource_info = java_client.get_resource_by_id(resource_id)
        user_profile = java_client.get_user_profile(user_id)

        plan_title = plan_info.get("title", "") if isinstance(plan_info, dict) else ""

        module_type = resource_info.get("moduleType", "document") if isinstance(resource_info, dict) else "document"
        module_title, resource_desc, source_resource_content, current_module_order = _extract_resource_context(resource_info)

        if module_type == "animation" and not source_resource_content:
            source_resource_content = _resolve_source_resource_content(plan_id, current_module_order, resource_id)
            if not source_resource_content and (module_title or resource_desc):
                source_resource_content = f"{module_title}\n\n{resource_desc}".strip()
                logger.info("  [MQ 消费] 动画源内容为空，使用模块标题/描述作为最小上下文")

        user_message = f"请为学习计划「{plan_title}」生成{module_type}类型的学习资源: {module_title}"
        if resource_desc:
            user_message += f"\n模块描述: {resource_desc}"

        logger.info("  [MQ 消费] 资源生成初始化:")
        logger.info("    计划: %s, 模块: %s, 类型: %s", plan_title, module_title, module_type)

        # 2. 运行 LangGraph 工作流（非流式，收集完整结果）
        # 路由决策：quiz/类型资源/动画/通用资源
        is_type_resource = module_type in ("mindmap", "summary", "code")
        is_animation = module_type == "animation"
        if module_type == "quiz":
            intent = "generate_quiz"
            next_node = "quiz_generator"
        elif is_animation:
            intent = "generate_animation"
            next_node = NODE_ANIMATION_SKILL_GENERATOR
        elif is_type_resource:
            intent = "generate_type_resource"
            next_node = "resource_type_generator"
        else:
            intent = "generate_resource"
            next_node = "rag_retriever"

        initial_state: AgentState = {
            "user_id": user_id,
            "plan_id": plan_id,
            "task_id": task_id,
            "session_id": f"mq-task-{task_id}",
            "user_message": user_message,
            "human_feedback": None,
            "chat_history": [],
            "user_profile": user_profile,
            "intent": intent,
            "next_node": next_node,
            "needs_human_confirm": False,
            "profile_update_needed": False,
            "learning_goal": user_message,
            "task_breakdown": {
                "modules": [{
                    "module_id": resource_id,
                    "title": module_title,
                    "description": resource_desc,
                    "resources": [{"resource_type": module_type}],
                }]
            },
            "task_breakdown_confirmed": True,
            "search_queries": [],
            "rag_results": [],
            "rag_context_chunks": [],
            "rag_sufficient": False,
            "rag_poor_module_ids": [],
            "retrieval_config": {},
            "review_passed": True,
            "review_feedback": "",
            "review_suggestions": [],
            "orchestrated_content": None,
            "module_list": [],
            "generated_content": None,
            "quiz_config": None,
            "quiz_questions": None,
            "quiz_answer": None,
            "quiz_result": None,
            "stream_events": [],
            "current_step": "",
            "error": None,
            "iteration_count": 0,
            "max_iterations": 10,
            "accumulated_context": "",
            "source_resource_content": source_resource_content,
            "background_generation": True,
        }

        graph = get_learning_graph()
        final_state = await graph.ainvoke(initial_state)

        error = final_state.get("error")
        if error:
            raise Exception(f"工作流执行失败: {error}")

        orchestrated = final_state.get("orchestrated_content") or {}
        module_list = final_state.get("module_list", [])
        generated_content = final_state.get("generated_content")
        quiz_questions = final_state.get("quiz_questions")
        quiz_config = final_state.get("quiz_config") or {}

        # 3. 持久化到 Java 后端 + MQ
        if quiz_questions:
            # quiz 资源：将题目列表存入 module_data.questions
            result_data = {
                "title": quiz_config.get("title", module_title),
                "description": quiz_config.get("description", resource_desc),
                "questions": quiz_questions,
                "total_questions": quiz_config.get("total", len(quiz_questions)),
            }
            module_data_json = json.dumps(result_data, ensure_ascii=False)
            logger.info("  [MQ 消费] quiz 资源: %d 道题目", len(quiz_questions))
        elif generated_content and (is_type_resource or is_animation):
            # 类型资源（mindmap/summary/code/animation）
            result_data = {
                "title": generated_content.get("title", module_title),
                "description": generated_content.get("description", resource_desc),
                "content": generated_content.get("content", ""),
                "module_title": generated_content.get("title", module_title),
            }
            if is_animation:
                result_data["html"] = generated_content.get("html", generated_content.get("content", ""))
                result_data["animationSpec"] = generated_content.get("animationSpec", {})
                result_data["duration"] = generated_content.get("duration")
                result_data["metadata"] = generated_content.get("metadata", {})
            module_data_json = json.dumps(result_data, ensure_ascii=False)
        elif orchestrated or module_list:
            first_module = module_list[0] if module_list else {}
            result_data = {
                "title": orchestrated.get("title") or first_module.get("title") or module_title,
                "description": orchestrated.get("description") or first_module.get("description") or resource_desc,
                "content": first_module.get("content", ""),
                "modules": module_list or orchestrated.get("modules", []),
                "summary": orchestrated.get("summary", ""),
            }
            images = first_module.get("images", [])
            if images:
                result_data["images"] = images
            module_data_json = json.dumps(result_data, ensure_ascii=False)
        else:
            raise Exception("工作流未生成有效内容")

        # 通过 Java 内部 API 持久化资源内容并更新任务状态（内部触发 SSE 推送）
        try:
            java_client.update_resource_content(resource_id, module_data_json, 2)
            java_client.update_generation_task(task_id, 2)
            logger.info("  [MQ 消费] 资源内容已通过内部 API 持久化")
        except Exception as e:
            logger.error("  [MQ 消费] 内部 API 落库失败: %s", e)
            raise

        logger.info("  [MQ 消费] 资源生成完成！")
        logger.info("    taskId=%s, resourceId=%s, 模块数=%s",
                    task_id, resource_id, len(module_list) if module_list else 0)

    async def _fail_task(self, task_id: int, user_id: int, reason: str):
        """任务失败处理（更新任务状态，内部触发 SSE 推送）"""
        try:
            java_client.update_generation_task(task_id, 3)
        except Exception:
            pass
        logger.error("  [MQ 消费] 任务失败: taskId=%s, 原因=%s", task_id, reason)


# 全局单例
mq_consumer = MQConsumer()
