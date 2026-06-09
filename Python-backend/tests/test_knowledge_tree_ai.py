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

    def _request(self, method, path, **kwargs):
        self.requests.append({"method": method, "path": path, **kwargs})
        return {"ok": True}


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

    def chat_json(self, messages, **kwargs):
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


def test_subdivide_node_creates_children():
    asyncio.run(_test_subdivide_node_creates_children())


async def _test_subdivide_node_creates_children():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "children": [
            {"title": "基础概念", "summary": "先学定义", "importance": 3, "difficulty": 1},
            {"title": "实践应用", "summary": "再看例子", "importance": 2, "difficulty": 2}
        ]
    }))

    events = [event async for event in service.subdivide_node(user_id=7, tree_id="tree_a", node_id="node_a", angle="按学习顺序")]

    assert len(client.created_nodes) == 2
    assert any(e["type"] == "nodes_created" for e in events)
    assert events[-1]["type"] == "done"


def test_suggest_subdivision_options_normalizes_llm_output():
    asyncio.run(_test_suggest_subdivision_options_normalizes_llm_output())


async def _test_suggest_subdivision_options_normalizes_llm_output():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "options": [
            {"angle": "by_concept", "label": "按概念拆", "rationale": "先把核心概念分开"},
            {"angle": "by_flow", "label": "按流程拆", "rationale": "再按学习顺序推进"},
            {"label": "按错误拆", "rationale": "覆盖常见误区"},
            {"angle": "", "label": "", "rationale": "空项应被过滤"},
        ],
        "caution": {"label": "先别拆", "rationale": "Aura UI 不使用这个分支"},
    }))

    result = await service.suggest_subdivision_options(
        user_id=7,
        tree_id="tree_a",
        node_id="node_a",
    )

    assert result["node_id"] == "node_a"
    assert [option["label"] for option in result["options"]] == ["按概念拆", "按流程拆", "按错误拆"]
    assert [option["angle"] for option in result["options"]] == ["by_concept", "by_flow", "按错误拆"]
    assert all("caution" not in option for option in result["options"])


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


def test_first_principles_creates_children_and_finishes_with_done():
    asyncio.run(_test_first_principles_creates_children_and_finishes_with_done())


async def _test_first_principles_creates_children_and_finishes_with_done():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "children": [
            {"title": "守恒关系", "summary": "找到不变量", "fpRelation": "foundation", "fpReason": "支撑推导"}
        ]
    }))

    events = [event async for event in service.first_principles(user_id=7, tree_id="tree_a", node_id="node_a")]

    assert client.created_nodes[0]["status"] == "pending"
    assert client.created_nodes[0]["isFundamental"] is True
    assert any(e["type"] == "nodes_created" for e in events)
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
