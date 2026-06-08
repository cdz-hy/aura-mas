"""MQ 动画资源生成链路测试。"""
import asyncio
import importlib
import json
import sys
from types import ModuleType
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mq_consumer(monkeypatch):
    module_name = "app.services.mq_consumer"
    parent = importlib.import_module("app.services")
    had_parent_attr = hasattr(parent, "mq_consumer")
    original_parent_attr = getattr(parent, "mq_consumer", None)
    had_module = module_name in sys.modules
    original_module = sys.modules.get(module_name)

    aio_pika = ModuleType("aio_pika")
    aio_pika.IncomingMessage = object
    aio_pika.RobustChannel = object
    aio_pika.RobustConnection = object
    aio_pika.DeliveryMode = type("DeliveryMode", (), {"PERSISTENT": 2})
    aio_pika.Message = lambda **kwargs: kwargs
    aio_pika.connect_robust = AsyncMock()
    monkeypatch.setitem(sys.modules, "aio_pika", aio_pika)

    learning_graph = ModuleType("app.graph.learning_graph")
    learning_graph.get_learning_graph = lambda: None
    monkeypatch.setitem(sys.modules, "app.graph.learning_graph", learning_graph)
    sys.modules.pop(module_name, None)

    imported = importlib.import_module(module_name)
    yield imported

    if had_module:
        sys.modules[module_name] = original_module
    else:
        sys.modules.pop(module_name, None)
    if had_parent_attr:
        setattr(parent, "mq_consumer", original_parent_attr)
    elif hasattr(parent, "mq_consumer"):
        delattr(parent, "mq_consumer")


class FakeGraph:
    def __init__(self, updates):
        self.updates = updates
        self.initial_state = None
        self.config = None

    async def astream(self, initial_state, config=None, stream_mode=None):
        self.initial_state = initial_state
        self.config = config
        self.stream_mode = stream_mode
        for update in self.updates:
            yield update


def test_mq_animation_task_routes_to_animation_generator_and_persists_html(mq_consumer):
    generated_html = "<!doctype html><html><body><main id='stage'><section class='beat active'>animation</section></main></body></html>"
    graph = FakeGraph([{
        "animation_skill_generator": {
            "generated_content": {
                "module_type": "animation",
                "title": "排序算法 - 动画演示",
                "description": "动画描述",
                "content": generated_html,
                "html": generated_html,
                "animationSpec": None,
                "duration": 60,
                "metadata": {"renderer": "jacky-motion"},
            },
            "stream_events": [],
        }
    }])

    animation_resource = {
        "id": 32,
        "moduleType": "animation",
        "moduleOrder": 3,
        "moduleData": json.dumps({}, ensure_ascii=False),
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
            patch.object(mq_consumer.java_client, "update_resource_content", side_effect=AssertionError("stale persistence API called")), \
            patch.object(mq_consumer.java_client, "update_generation_task", side_effect=AssertionError("stale task API called")), \
            patch.object(mq_consumer.java_client, "complete_generation_task") as complete_generation_task:
        asyncio.run(mq_consumer.MQConsumer()._process_task(99, 1, 32, 7, "animation"))

    state = graph.initial_state
    assert graph.stream_mode == "updates"
    assert graph.config["configurable"]["thread_id"] == "mq-task-99"
    assert state["intent"] == "generate_animation"
    assert state["next_node"] == "animation_skill_generator"
    assert state["background_generation"] is True
    assert state["learning_goal"] == ""
    assert "冒泡排序" in state["source_resource_content"]

    complete_generation_task.assert_called_once()
    task_id, module_data_json = complete_generation_task.call_args.args
    assert task_id == 99
    module_data = json.loads(module_data_json)
    assert module_data["content"] == generated_html
    assert module_data["html"] == generated_html
    assert module_data["metadata"]["renderer"] == "jacky-motion"


def test_mq_text_task_persists_first_module_content_from_stream(mq_consumer):
    graph = FakeGraph([{
        "content_orchestrator": {
            "module_list": [{
                "module_order": 1,
                "module_id": 34,
                "title": "经典序列模型与神经网络基础",
                "content": "这里是经典序列模型与神经网络基础的学习正文。",
                "description": "介绍 HMM、RNN 与神经网络基础。",
            }],
            "orchestrated_content": {"summary": "已生成正文"},
            "stream_events": [],
        }
    }])

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
            patch.object(mq_consumer.java_client, "update_resource_content", side_effect=AssertionError("stale persistence API called")), \
            patch.object(mq_consumer.java_client, "update_generation_task", side_effect=AssertionError("stale task API called")), \
            patch.object(mq_consumer.java_client, "complete_generation_task") as complete_generation_task:
        asyncio.run(mq_consumer.MQConsumer()._process_task(34, 1, 34, 7, "text"))

    state = graph.initial_state
    assert graph.stream_mode == "updates"
    assert graph.config["configurable"]["thread_id"] == "mq-task-34"
    assert state["intent"] == "generate_resource"
    assert state["next_node"] == "rag_retriever"
    assert state["background_generation"] is True

    complete_generation_task.assert_called_once()
    task_id, module_data_json = complete_generation_task.call_args.args
    assert task_id == 34
    module_data = json.loads(module_data_json)
    assert module_data["content"] == "这里是经典序列模型与神经网络基础的学习正文。"
    assert module_data["modules"][0]["title"] == "经典序列模型与神经网络基础"


def test_mq_task_with_empty_graph_output_raises_no_content_error(mq_consumer):
    graph = FakeGraph([])
    text_resource = {
        "id": 35,
        "moduleType": "text",
        "moduleOrder": 1,
        "moduleData": json.dumps({"module_title": "空输出模块"}, ensure_ascii=False),
    }

    with patch.object(mq_consumer, "get_learning_graph", return_value=graph), \
            patch.object(mq_consumer.java_client, "get_plan", return_value={"title": "计划"}), \
            patch.object(mq_consumer.java_client, "get_resource_by_id", return_value=text_resource), \
            patch.object(mq_consumer.java_client, "get_user_profile", return_value={}):
        with pytest.raises(Exception, match="工作流未生成有效内容"):
            asyncio.run(mq_consumer.MQConsumer()._process_task(35, 1, 35, 7, "text"))
