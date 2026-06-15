"""MQ 动画资源生成链路测试"""
import asyncio
import json
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

aio_pika = ModuleType("aio_pika")
aio_pika.IncomingMessage = object
aio_pika.RobustChannel = object
aio_pika.RobustConnection = object
aio_pika.connect_robust = AsyncMock()
sys.modules.setdefault("aio_pika", aio_pika)

learning_graph = ModuleType("app.graph.learning_graph")
learning_graph.get_learning_graph = lambda: None
sys.modules.setdefault("app.graph.learning_graph", learning_graph)

from app.services import mq_consumer
from app.services.mq_consumer import MQConsumer


def test_mq_animation_task_routes_to_animation_generator_and_persists_html():
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={
        "error": None,
        "generated_content": {
            "module_type": "animation",
            "title": "排序算法 - 动画演示",
            "description": "动画描述",
            "content": "<!doctype html><html><body>animation</body></html>",
            "html": "<!doctype html><html><body>animation</body></html>",
            "animationSpec": {"beats": [{"title": "比较"}]},
            "duration": 60,
            "metadata": {"renderer": "aura-teaching-animation"},
        },
        "module_list": [],
        "orchestrated_content": None,
        "quiz_questions": None,
        "quiz_config": None,
    })

    animation_resource = {
        "id": 32,
        "moduleType": "animation",
        "moduleOrder": 3,
        "moduleData": json.dumps({
            "module_title": "排序算法",
            "module_description": "理解比较、交换和有序区",
            "title": "排序动画",
        }, ensure_ascii=False),
    }
    text_resource = {
        "id": 12,
        "moduleType": "text",
        "moduleOrder": 3,
        "status": 2,
        "moduleData": json.dumps({
            "content": "冒泡排序会反复比较相邻元素，并把较大的元素向后交换。",
        }, ensure_ascii=False),
    }

    with patch.object(mq_consumer, "get_learning_graph", return_value=graph), \
            patch.object(mq_consumer.java_client, "get_plan", return_value={"title": "算法学习"}), \
            patch.object(mq_consumer.java_client, "get_resource_by_id", return_value=animation_resource), \
            patch.object(mq_consumer.java_client, "get_user_profile", return_value={}), \
            patch.object(mq_consumer.java_client, "get_resources_by_module", return_value=[animation_resource, text_resource]), \
            patch.object(mq_consumer.java_client, "update_resource_content") as update_resource_content, \
            patch.object(mq_consumer.java_client, "update_generation_task") as update_generation_task:
        asyncio.run(
            MQConsumer()._process_task(
                task_id=99,
                plan_id=1,
                resource_id=32,
                user_id=7,
                agent_chain="animation",
            )
        )

    state = graph.ainvoke.call_args.args[0]
    assert state["intent"] == "generate_animation"
    assert state["next_node"] == "animation_skill_generator"
    assert "冒泡排序" in state["source_resource_content"]

    update_resource_content.assert_called_once()
    resource_id, module_data_json, status = update_resource_content.call_args.args
    assert resource_id == 32
    assert status == 2

    module_data = json.loads(module_data_json)
    assert module_data["content"].startswith("<!doctype html>")
    assert module_data["html"] == module_data["content"]
    assert module_data["animationSpec"]["beats"][0]["title"] == "比较"
    update_generation_task.assert_called_once_with(99, 2)


def test_mq_text_task_marks_background_generation_and_persists_module_content():
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={
        "error": None,
        "generated_content": {
            "module_order": 1,
            "module_id": 34,
            "title": "经典序列模型与神经网络基础",
            "content": "这里是经典序列模型与神经网络基础的学习正文。",
            "description": "介绍 HMM、RNN 与神经网络基础。",
        },
        "module_list": [{
            "module_order": 1,
            "module_id": 34,
            "title": "经典序列模型与神经网络基础",
            "content": "这里是经典序列模型与神经网络基础的学习正文。",
            "description": "介绍 HMM、RNN 与神经网络基础。",
        }],
        "orchestrated_content": None,
        "quiz_questions": None,
        "quiz_config": None,
    })

    text_resource = {
        "id": 34,
        "moduleType": "text",
        "moduleOrder": 1,
        "moduleData": json.dumps({
            "module_title": "经典序列模型与神经网络基础",
            "module_description": "理解经典序列建模与神经网络基本思想",
            "title": "图文资源",
        }, ensure_ascii=False),
    }

    with patch.object(mq_consumer, "get_learning_graph", return_value=graph), \
            patch.object(mq_consumer.java_client, "get_plan", return_value={"title": "新学习计划"}), \
            patch.object(mq_consumer.java_client, "get_resource_by_id", return_value=text_resource), \
            patch.object(mq_consumer.java_client, "get_user_profile", return_value={}), \
            patch.object(mq_consumer.java_client, "update_resource_content") as update_resource_content, \
            patch.object(mq_consumer.java_client, "update_generation_task") as update_generation_task:
        asyncio.run(
            MQConsumer()._process_task(
                task_id=34,
                plan_id=1,
                resource_id=34,
                user_id=7,
                agent_chain="text",
            )
        )

    state = graph.ainvoke.call_args.args[0]
    assert state["intent"] == "generate_resource"
    assert state["next_node"] == "rag_retriever"
    assert state["background_generation"] is True

    update_resource_content.assert_called_once()
    resource_id, module_data_json, status = update_resource_content.call_args.args
    assert resource_id == 34
    assert status == 2

    module_data = json.loads(module_data_json)
    assert module_data["content"] == "这里是经典序列模型与神经网络基础的学习正文。"
    assert module_data["modules"][0]["content"] == "这里是经典序列模型与神经网络基础的学习正文。"
    update_generation_task.assert_called_once_with(34, 2)
