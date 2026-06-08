import importlib
import json
import sys
from types import ModuleType
from unittest.mock import patch

import pytest


@pytest.fixture
def resource_chat(monkeypatch):
    module_name = "app.api.v1.endpoints.resource_chat"
    parent = importlib.import_module("app.api.v1.endpoints")
    had_parent_attr = hasattr(parent, "resource_chat")
    original_parent_attr = getattr(parent, "resource_chat", None)
    had_module = module_name in sys.modules
    original_module = sys.modules.get(module_name)

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
        setattr(parent, "resource_chat", original_parent_attr)
    elif hasattr(parent, "resource_chat"):
        delattr(parent, "resource_chat")


def test_save_modules_as_resources_uses_each_module_type(resource_chat):
    modules = [
        {
            "module_order": 1,
            "module_type": "code",
            "title": "代码示例",
            "content": "print('hello')",
            "description": "Python 输出",
            "metadata": {"key_concepts": ["print"]},
            "references": ["[1] docs"],
        },
        {
            "module_order": 2,
            "module_type": ["unknown"],
            "title": "兜底图文",
            "content": "正文内容",
            "description": "未知类型应归一化为 text",
        },
    ]

    with patch.object(resource_chat.java_client, "get_plan_resources", return_value=[]), \
            patch.object(resource_chat.java_client, "create_resources_bulk", return_value=[{"id": 101}, {"id": 102}]) as bulk:
        ids = resource_chat._save_modules_as_resources(9, modules, {"title": "计划"})

    assert ids == [101, 102]
    resources = bulk.call_args.args[0]
    assert resources[0]["moduleType"] == "code"
    assert resources[1]["moduleType"] == "text"
    first_data = json.loads(resources[0]["moduleData"])
    assert first_data["content"] == "print('hello')"
    assert first_data["key_concepts"] == ["print"]
    assert first_data["references"] == ["[1] docs"]
    second_data = json.loads(resources[1]["moduleData"])
    assert second_data["title"] == "兜底图文"
    assert second_data["content"] == "正文内容"
    assert second_data["description"] == "未知类型应归一化为 text"
