import asyncio

from app.services.knowledge_tree_ai import KnowledgeTreeAiService


class BlockingLlm:
    def __init__(self):
        self.allow_first_chunk = None
        self.allow_second_chunk = None
        self.chunk_sent = None

    def chat_stream(self, messages, **kwargs):
        self.allow_first_chunk.wait(timeout=2)
        yield "第一段"
        self.chunk_sent.set()
        self.allow_second_chunk.wait(timeout=2)
        yield "第二段"


class FakeJavaClient:
    def __init__(self):
        self.messages = []
        self.created_nodes = []
        self.created_resources = []
        self.requests = []
        self.plan_resources = []
        self.tree_response = {
            "tree": {
                "id": "tree_a",
                "planId": 42,
                "title": "Learn Python",
                "contextSummary": "计划目标：能用 Python 写小工具",
            },
            "nodes": [
                {"id": "node_root", "treeId": "tree_a", "parentId": None, "title": "Root", "summary": "root summary"},
                {"id": "node_a", "treeId": "tree_a", "parentId": "node_root", "title": "变量", "summary": "变量摘要", "content": "变量内容"},
                {"id": "node_sibling", "treeId": "tree_a", "parentId": "node_root", "title": "函数", "summary": "函数摘要"},
                {"id": "node_child", "treeId": "tree_a", "parentId": "node_a", "title": "赋值", "summary": "赋值摘要"},
            ],
        }

    def add_tree_message(self, node_id, payload):
        message = {"nodeId": node_id, **payload}
        self.messages.append(message)
        return message

    def create_tree_node(self, payload):
        node = {"id": f"node_{len(self.created_nodes) + 1}", **payload}
        self.created_nodes.append(node)
        return node

    def create_resource(self, plan_id, module_type, module_data, module_order=0, parent_id=None, status=2, generated_by_agent=None):
        resource = {
            "id": len(self.created_resources) + 123,
            "planId": plan_id,
            "moduleType": module_type,
            "moduleData": module_data,
            "moduleOrder": module_order,
            "parentId": parent_id,
            "status": status,
            "generatedByAgent": generated_by_agent,
        }
        self.created_resources.append(resource)
        return resource

    def get_plan_resources(self, plan_id):
        return self.plan_resources

    def get_tree(self, tree_id, user_id):
        return self.tree_response

    def _request(self, method, path, **kwargs):
        self.requests.append({"method": method, "path": path, **kwargs})
        return {"ok": True}

    def get_tree_messages(self, node_id):
        return [
            {"role": "USER", "content": "想看例子"},
            {"role": "ASSISTANT", "content": "可以从赋值开始"},
        ]


class FakeRetriever:
    async def search(self, query, **kwargs):
        return {
            "final_results": [{"id": "r1", "payload": {"content": "相关资料"}}],
            "context_chunks": [{"content": "相关资料", "doc_title": "资料"}],
        }


class FakeLlm:
    def __init__(self, chunks):
        self.chunks = chunks

    def chat_stream(self, messages, **kwargs):
        yield from self.chunks


class FakeJsonLlm:
    def __init__(self, data):
        self.data = data
        self.messages = []
        self.calls = 0

    def chat_json(self, messages, **kwargs):
        self.messages.append(messages)
        if isinstance(self.data, list):
            index = min(self.calls, len(self.data) - 1)
            self.calls += 1
            return self.data[index]
        self.calls += 1
        return self.data


def test_explain_node_stream_persists_user_and_assistant():
    asyncio.run(_test_explain_node_stream_persists_user_and_assistant())


async def _test_explain_node_stream_persists_user_and_assistant():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeLlm(["你好", "，世界"]))

    events = [event async for event in service.explain_node(user_id=7, tree_id="tree_a", node_id="node_a", message="解释")]

    assert client.messages[0]["role"] == "USER"
    assert client.messages[-1]["role"] == "ASSISTANT"
    assert any(e["type"] == "stream_text" for e in events)
    assert events[-1]["type"] == "done"


def test_explain_node_yields_chunks_before_sync_stream_finishes():
    asyncio.run(_test_explain_node_yields_chunks_before_sync_stream_finishes())


async def _test_explain_node_yields_chunks_before_sync_stream_finishes():
    import threading

    client = FakeJavaClient()
    llm = BlockingLlm()
    llm.allow_first_chunk = threading.Event()
    llm.allow_second_chunk = threading.Event()
    llm.chunk_sent = threading.Event()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=llm)

    stream = service.explain_node(user_id=7, tree_id="tree_a", node_id="node_a", message="解释")
    assert (await anext(stream))["type"] == "start"
    assert (await anext(stream))["type"] == "search_results"

    llm.allow_first_chunk.set()
    event = await stream.__anext__()

    assert event == {"type": "stream_text", "content": "第一段"}
    assert llm.chunk_sent.is_set()
    assert client.messages[-1]["role"] == "USER"

    llm.allow_second_chunk.set()
    remaining = [event async for event in stream]
    assert any(e["type"] == "message_saved" for e in remaining)
    assert remaining[-1]["type"] == "done"


def test_subdivide_node_creates_group_node_with_enriched_context():
    asyncio.run(_test_subdivide_node_creates_group_node_with_enriched_context())


async def _test_subdivide_node_creates_group_node_with_enriched_context():
    client = FakeJavaClient()
    json_llm = FakeJsonLlm({
        "middle_title": "按学习顺序拆变量",
        "children": [
            {"title": "基础概念", "summary": "先学定义", "importance": 3, "difficulty": 1},
            {"title": "实践应用", "summary": "再看例子", "importance": 2, "difficulty": 2}
        ]
    })
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=json_llm)

    events = [event async for event in service.subdivide_node(user_id=7, tree_id="tree_a", node_id="node_a", angle="按学习顺序")]

    assert len(client.created_nodes) == 3
    group = client.created_nodes[0]
    assert group["title"] == "按学习顺序拆变量"
    assert group["parentId"] == "node_a"
    assert client.created_nodes[1]["parentId"] == group["id"]
    assert client.created_nodes[2]["parentId"] == group["id"]
    assert any(e["type"] == "nodes_created" for e in events)
    assert events[-1]["type"] == "done"
    prompt = json_llm.messages[0][1]["content"]
    assert "当前节点：变量" in prompt
    assert "节点路径：Root > 变量" in prompt
    assert "兄弟节点：函数" in prompt
    assert "已有子节点：赋值" in prompt
    assert "计划目标：Learn Python" in prompt
    assert "最近对话" in prompt and "想看例子" in prompt
    assert "目标数量：3-4" in prompt


def test_suggest_subdivision_options_normalizes_llm_output():
    asyncio.run(_test_suggest_subdivision_options_normalizes_llm_output())


async def _test_suggest_subdivision_options_normalizes_llm_output():
    client = FakeJavaClient()
    json_llm = FakeJsonLlm({
        "options": [
            {"angle": "by_concept", "label": "按概念拆", "rationale": "先把核心概念分开"},
            {"angle": "by_flow", "label": "按流程拆", "rationale": "再按学习顺序推进"},
            {"label": "按错误拆", "rationale": "覆盖常见误区"},
            {"angle": "", "label": "", "rationale": "空项应被过滤"},
        ],
        "caution": {"label": "先别拆", "rationale": "节点已经足够细，继续拆会增加噪音"},
    })
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=json_llm)

    result = await service.suggest_subdivision_options(
        user_id=7,
        tree_id="tree_a",
        node_id="node_a",
        mode="Medium",
    )

    assert result["node_id"] == "node_a"
    assert [option["label"] for option in result["options"]] == ["按概念拆", "按流程拆", "按错误拆"]
    assert [option["angle"] for option in result["options"]] == ["by_concept", "by_flow", "按错误拆"]
    assert all("caution" not in option for option in result["options"])
    assert result["caution"] == {"label": "先别拆", "rationale": "节点已经足够细，继续拆会增加噪音"}
    assert "Medium" in json_llm.messages[0][1]["content"]
    assert "目标数量：5-7" in json_llm.messages[0][1]["content"]


def test_multi_angle_subdivide_creates_group_nodes_and_children():
    asyncio.run(_test_multi_angle_subdivide_creates_group_nodes_and_children())


async def _test_multi_angle_subdivide_creates_group_nodes_and_children():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "groups": [
            {
                "angle": "by_concept",
                "label": "按概念拆",
                "children": [
                    {"title": "变量是什么", "summary": "理解变量的定义"},
                    {"title": "类型是什么", "summary": "理解类型的约束"},
                ],
            },
            {
                "angle": "by_flow",
                "label": "按流程拆",
                "children": [
                    {"title": "赋值", "summary": "把值绑定到变量"},
                ],
            },
        ],
    }))

    events = [event async for event in service.multi_angle_subdivide(
        user_id=7,
        tree_id="tree_a",
        node_id="node_parent",
        angles=[
            {"angle": "by_concept", "label": "按概念拆", "rationale": "概念清楚"},
            {"angle": "by_flow", "label": "按流程拆", "rationale": "按顺序学"},
        ],
    )]

    created = client.created_nodes
    assert created[0]["title"] == "按概念拆"
    assert created[0]["parentId"] == "node_parent"
    assert created[1]["title"] == "变量是什么"
    assert created[1]["parentId"] == created[0]["id"]
    assert created[3]["title"] == "按流程拆"
    assert created[3]["parentId"] == "node_parent"
    assert any(event["type"] == "nodes_created" for event in events)
    assert events[-1]["type"] == "done"


def test_first_principles_grows_layer_by_layer_and_finishes_with_done():
    asyncio.run(_test_first_principles_grows_layer_by_layer_and_finishes_with_done())


async def _test_first_principles_grows_layer_by_layer_and_finishes_with_done():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm([
        {
            "children": [
                {"title": "守恒关系", "summary": "找到不变量", "fpRelation": "foundation", "fpReason": "支撑推导", "isFundamental": False}
            ]
        },
        {
            "children": [
                {"title": "等价变换", "summary": "守恒的数学表达", "fpRelation": "derives", "fpReason": "继续触底", "isFundamental": True}
            ]
        },
    ]))

    events = [event async for event in service.first_principles(user_id=7, tree_id="tree_a", node_id="node_a")]

    assert client.created_nodes[0]["status"] == "pending"
    assert client.created_nodes[0]["isFundamental"] is False
    assert client.created_nodes[0]["fpRelation"] == "foundation"
    assert client.created_nodes[0]["fpReason"] == "支撑推导"
    assert client.created_nodes[1]["parentId"] == client.created_nodes[0]["id"]
    assert client.created_nodes[1]["fpRelation"] == "derives"
    assert client.created_nodes[1]["isFundamental"] is True
    node_events = [event for event in events if event["type"] == "nodes_created"]
    assert len(node_events) == 2
    assert node_events[0]["nodes"][0]["title"] == "守恒关系"
    assert node_events[1]["nodes"][0]["title"] == "等价变换"
    assert events[-1]["type"] == "done"


def test_quiz_node_creates_quiz_resource_and_emits_resource_generated():
    asyncio.run(_test_quiz_node_creates_quiz_resource_and_emits_resource_generated())


async def _test_quiz_node_creates_quiz_resource_and_emits_resource_generated():
    client = FakeJavaClient()
    client.plan_resources = [{"moduleOrder": 4}]
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "questions": [
            {
                "question_text": "什么是梯度？",
                "options": ["方向", "颜色"],
                "correct_answer": "方向",
                "explanation": "梯度表示变化最快方向。",
                "difficulty": 2,
            }
        ]
    }))

    events = [event async for event in service.quiz_node(user_id=7, tree_id="tree_a", node_id="node_a", plan_id=42)]

    assert client.created_resources[0]["planId"] == 42
    assert client.created_resources[0]["moduleType"] == "quiz"
    assert client.created_resources[0]["moduleOrder"] == 5
    assert client.created_resources[0]["moduleData"]["questions"][0]["question"] == "什么是梯度？"
    assert client.created_resources[0]["moduleData"]["questions"][0]["correctAnswer"] == "方向"
    assert any(event == {
        "type": "resource_generated",
        "resources": [{"id": 123, "type": "quiz", "title": "节点练习题"}],
    } for event in events)
    assert events[-1]["type"] == "done"


def test_flashcards_node_creates_text_resource_with_cards_when_no_note_exists():
    asyncio.run(_test_flashcards_node_creates_text_resource_with_cards_when_no_note_exists())


async def _test_flashcards_node_creates_text_resource_with_cards_when_no_note_exists():
    client = FakeJavaClient()
    client.plan_resources = [{"id": 9, "moduleOrder": 2, "moduleType": "quiz", "moduleData": {"title": "other"}}]
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "cards": [
            {"question_text": "梯度是什么？", "answer_text": "变化最快方向", "level": 1},
        ]
    }))

    events = [event async for event in service.flashcards_node(user_id=7, tree_id="tree_a", node_id="node_a", plan_id=42)]

    assert client.created_resources[0]["planId"] == 42
    assert client.created_resources[0]["moduleType"] == "text"
    assert client.created_resources[0]["moduleOrder"] == 3
    assert client.created_resources[0]["moduleData"]["flashcards"] == [
        {"question": "梯度是什么？", "answer": "变化最快方向", "difficulty": 1}
    ]
    assert client.requests == []
    assert any(event == {
        "type": "flashcards_generated",
        "cards": [{"question": "梯度是什么？", "answer": "变化最快方向", "difficulty": 1}],
    } for event in events)
    assert events[-1]["type"] == "done"


def test_flashcards_node_saves_cards_to_existing_note():
    asyncio.run(_test_flashcards_node_saves_cards_to_existing_note())


async def _test_flashcards_node_saves_cards_to_existing_note():
    client = FakeJavaClient()
    client.plan_resources = [{"id": 9, "moduleData": {"nodeId": "node_a", "noteId": 88}}]
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "flashcards": [
            {"question": "梯度是什么？", "answer": "变化最快方向", "difficulty": 2},
        ]
    }))

    events = [event async for event in service.flashcards_node(user_id=7, tree_id="tree_a", node_id="node_a", plan_id=42)]

    assert client.created_resources == []
    save_request = client.requests[0]
    assert save_request["method"] == "POST"
    assert save_request["path"] == "/api/flashcard/internal/save"
    assert save_request["json"]["userId"] == 7
    assert save_request["json"]["noteId"] == 88
    assert save_request["json"]["cards"] == [
        {"question": "梯度是什么？", "answer": "变化最快方向", "difficulty": 2}
    ]
    assert any(event == {
        "type": "flashcards_generated",
        "cards": [{"question": "梯度是什么？", "answer": "变化最快方向", "difficulty": 2}],
    } for event in events)
    assert events[-1]["type"] == "done"
