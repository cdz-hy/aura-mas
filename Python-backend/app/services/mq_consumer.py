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
from app.schemas.sse_bridge import graph_step_to_sse
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

            # 恢复上次崩溃遗留的卡死任务
            await self._recover_stuck_tasks()
        except Exception as e:
            logger.warning("MQ 消费者启动失败（MQ 可能未就绪）: %s", e)
            self._running = False

    async def _recover_stuck_tasks(self):
        """启动时扫描卡死任务（task_status=1, resource_status=1），重新入队"""
        import asyncio as _asyncio
        try:
            # 等待 Java 后端就绪
            for attempt in range(3):
                try:
                    loop = _asyncio.get_event_loop()
                    stuck_tasks = await loop.run_in_executor(None, java_client.get_stuck_tasks)
                    break
                except Exception as e:
                    logger.warning("[恢复] Java 后端未就绪，重试 (%d/3): %s", attempt + 1, e)
                    if attempt < 2:
                        await _asyncio.sleep(3)
                    else:
                        logger.error("[恢复] Java 后端不可用，跳过恢复")
                        return

            logger.info("[恢复] 查询卡死任务结果: %d 条", len(stuck_tasks))
            if not stuck_tasks:
                return

            for task in stuck_tasks:
                task_id = task.get("id")
                plan_id = task.get("planId")
                resource_id = task.get("resourceId")
                logger.info("[恢复] 处理任务: taskId=%s, planId=%s, resourceId=%s, retryCount=%s",
                            task_id, plan_id, resource_id, task.get("retryCount", 0))
                try:
                    plan_info = java_client.get_plan(plan_id)
                    user_id = plan_info.get("userId") if isinstance(plan_info, dict) else None
                except Exception as e:
                    logger.warning("[恢复] 获取计划信息失败: %s", e)
                    user_id = None
                if not all([task_id, plan_id, resource_id, user_id]):
                    logger.warning("[恢复] 跳过不完整的任务: taskId=%s, userId=%s", task_id, user_id)
                    continue
                message = {
                    "taskId": task_id,
                    "planId": plan_id,
                    "resourceId": resource_id,
                    "userId": user_id,
                    "agentChain": task.get("agentChain", "plan_chat"),
                }
                payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
                await self._channel.default_exchange.publish(
                    aio_pika.Message(
                        body=payload,
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        content_type="application/json",
                    ),
                    routing_key=self.QUEUE_GENERATION,
                )
                logger.info("[恢复] 任务 %s 已重新入队 (resourceId=%s)", task_id, resource_id)
        except Exception as e:
            logger.error("[恢复] 扫描卡死任务失败: %s", e, exc_info=True)

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
        # 记录投递次数（RabbitMQ header，首次为1）
        delivery_count = 0
        if message.headers:
            x_death = message.headers.get("x-death")
            if x_death and isinstance(x_death, list) and len(x_death) > 0:
                delivery_count = x_death[0].get("count", 0)

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
            logger.info("    taskId=%s, planId=%s, resourceId=%s, userId=%s, deliveryCount=%s",
                        task_id, plan_id, resource_id, user_id, delivery_count + 1)
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
                # 标记任务失败，Java 端会根据 retryCount 决定是否自动重试
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

        # 2. 运行 LangGraph 工作流（流式，逐步收集结果）
        # 路由决策：quiz/类型资源/动画/通用资源
        is_type_resource = module_type in ("mindmap", "summary", "code", "podcast", "pptx")
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
            "learning_goal": module_title,
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

        # 流式执行图工作流，逐步收集结果
        orchestrated = {}
        module_list = []
        generated_content = None
        quiz_questions = None
        quiz_config = {}

        graph = get_learning_graph()
        config = {"configurable": {"thread_id": f"mq-task-{task_id}"}}
        async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_output is None:
                    continue
                if isinstance(node_output, dict):
                    if node_output.get("orchestrated_content"):
                        orchestrated = node_output["orchestrated_content"]
                    if node_output.get("module_list"):
                        module_list = node_output["module_list"]
                    if node_output.get("quiz_questions"):
                        quiz_questions = node_output["quiz_questions"]
                    if node_output.get("quiz_config"):
                        quiz_config = node_output["quiz_config"]
                    if node_output.get("generated_content"):
                        generated_content = node_output["generated_content"]
                for sse_data in graph_step_to_sse(node_name, node_output):
                    try:
                        parsed = json.loads(sse_data.replace("data: ", "").strip())
                        if parsed.get("type") == "progress":
                            logger.info("  [MQ 消费] 进度: %s", parsed.get("content", ""))
                    except Exception:
                        pass

        # 3. 持久化到 Java 后端（保留原始 title）
        if quiz_questions:
            result_data = {
                "title": quiz_config.get("title", module_title),
                "description": quiz_config.get("description", resource_desc),
                "questions": quiz_questions,
                "total_questions": quiz_config.get("total", len(quiz_questions)),
            }
            module_data_json = json.dumps(result_data, ensure_ascii=False)
            logger.info("  [MQ 消费] quiz 资源: %d 道题目", len(quiz_questions))
        elif generated_content and (is_type_resource or is_animation):
            result_data = {
                "title": module_title,
                "description": resource_desc,
                "content": generated_content.get("content", ""),
                "module_title": module_title,
            }
            if is_animation or module_type == "podcast":
                result_data["html"] = generated_content.get("html", generated_content.get("content", ""))
            if module_type == "pptx":
                result_data["html"] = generated_content.get("content", "")
                result_data["pptx_filename"] = generated_content.get("pptx_filename", "")
                result_data["pptx_url"] = generated_content.get("pptx_url", "")
                result_data["slide_count"] = generated_content.get("slide_count", 0)
            if is_animation:
                result_data["animationSpec"] = generated_content.get("animationSpec", {})
                result_data["duration"] = generated_content.get("duration")
                result_data["metadata"] = generated_content.get("metadata", {})
                result_data["narration"] = generated_content.get("narration")
                result_data["videoExports"] = generated_content.get("videoExports", {})
            module_data_json = json.dumps(result_data, ensure_ascii=False)
        elif orchestrated or module_list:
            first_module = module_list[0] if module_list else {}
            result_data = {
                "title": module_title,
                "description": resource_desc,
                "content": first_module.get("content", ""),
                "modules": module_list or orchestrated.get("modules", []),
                "summary": orchestrated.get("summary", ""),
                "module_title": module_title,
            }
            images = first_module.get("images", [])
            if images:
                result_data["images"] = images
            module_data_json = json.dumps(result_data, ensure_ascii=False)
        else:
            raise Exception("工作流未生成有效内容")

        # 通过 Java 内部 API 原子性持久化资源内容并更新任务状态（同一事务，内部触发 SSE 推送）
        try:
            java_client.complete_generation_task(task_id, module_data_json)
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
