"""动画补充资源持久化测试"""
import json
import sys
from types import ModuleType
from unittest.mock import patch

learning_graph = ModuleType("app.graph.learning_graph")
learning_graph.get_learning_graph = lambda: None
sys.modules.setdefault("app.graph.learning_graph", learning_graph)

from app.api.v1.endpoints import resource_chat


def test_persist_animation_generated_content_as_animation_resource():
    generated_content = {
        "module_type": "animation",
        "title": "排序算法 - 动画演示",
        "description": "用动画解释排序流程",
        "html": "<!doctype html><html><body>animation</body></html>",
        "content": "<!doctype html><html><body>animation</body></html>",
        "animationSpec": {"beats": [{"title": "比较"}]},
        "duration": 60,
        "metadata": {"renderer": "aura-teaching-animation"},
    }

    with patch.object(resource_chat.java_client, "create_resource", return_value={"id": 123}) as create_resource, \
            patch.object(resource_chat.java_client, "create_dialogue", return_value={"id": 456}):
        resources = resource_chat._persist_generated_resources(
            plan_id_int=1,
            user_id=2,
            is_quiz=False,
            resource_type="animation",
            title="排序算法",
            description="",
            module_list=[],
            orchestrated_content=None,
            quiz_questions=None,
            quiz_config=None,
            generated_content=generated_content,
            current_module_order=7,
            session_id="session-1",
        )

    assert resources == [{"id": 123, "type": "animation", "title": "排序算法 - 动画演示"}]

    kwargs = create_resource.call_args.kwargs
    assert kwargs["module_type"] == "animation"
    assert kwargs["module_order"] == 7
    assert kwargs["generated_by_agent"] == "animation_skill_generator"

    module_data = json.loads(kwargs["module_data"])
    assert module_data["content"] == generated_content["html"]
    assert module_data["html"] == generated_content["html"]
    assert module_data["animationSpec"] == generated_content["animationSpec"]


def test_extract_animation_source_context_prefers_content_then_html_then_metadata():
    resource_with_html = {
        "moduleOrder": 5,
        "moduleData": json.dumps({
            "content": "",
            "html": "<!doctype html><html><body>已有动画</body></html>",
            "module_title": "已有动画标题",
            "module_description": "已有描述",
        }, ensure_ascii=False),
    }

    module_order, source = resource_chat._extract_source_resource_context(
        resource_with_html,
        fallback_title="兜底标题",
        fallback_description="兜底描述",
    )

    assert module_order == 5
    assert "已有动画" in source

    resource_without_body = {
        "moduleOrder": 6,
        "moduleData": {
            "module_title": "经典序列模型",
            "module_description": "理解 RNN 和隐藏状态",
        },
    }

    module_order, source = resource_chat._extract_source_resource_context(
        resource_without_body,
        fallback_title="兜底标题",
        fallback_description="兜底描述",
    )

    assert module_order == 6
    assert "经典序列模型" in source
    assert "隐藏状态" in source
