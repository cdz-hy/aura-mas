import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import knowledge_tree


class FakeJavaClient:
    def __init__(self):
        self.validated = []
        self.verified = []
        self.plan_checks = []
        self.fail_verify = False
        self.plan_tree_id = "tree_a"

    def validate_ticket(self, ticket):
        self.validated.append(ticket)
        return {"user_id": 7}

    def get_or_create_tree(self, plan_id, user_id):
        return {"tree": {"id": "tree_a", "planId": plan_id, "userId": user_id}, "nodes": []}

    def get_tree_by_plan(self, plan_id, user_id):
        self.plan_checks.append((plan_id, user_id))
        return {"tree": {"id": self.plan_tree_id, "planId": plan_id, "userId": user_id}, "nodes": []}

    def verify_tree_node_access(self, tree_id, node_id, user_id):
        self.verified.append((tree_id, node_id, user_id))
        if self.fail_verify:
            raise Exception("not found")
        return {"ok": True}


class FakeService:
    async def explain_node(self, **kwargs):
        yield {"type": "start", "node_id": kwargs["node_id"]}
        yield {"type": "stream_text", "content": "你好"}
        yield {"type": "done"}

    async def subdivide_node(self, **kwargs):
        yield {"type": "start", "node_id": kwargs["node_id"]}
        yield {"type": "nodes_created", "nodes": [{"id": "node_1"}]}
        yield {"type": "done"}

    async def first_principles(self, **kwargs):
        yield {"type": "nodes_created", "nodes": [{"id": "fp_1"}]}
        yield {"type": "done"}

    async def quiz_node(self, **kwargs):
        yield {"type": "resource_generated", "resources": [{"id": 123, "type": "quiz", "title": "节点练习题"}]}
        yield {"type": "done"}

    async def flashcards_node(self, **kwargs):
        yield {"type": "flashcards_generated", "cards": [{"question": "Q", "answer": "A", "difficulty": 1}]}
        yield {"type": "done"}


def make_client(monkeypatch):
    app = FastAPI()
    app.include_router(knowledge_tree.router, prefix="/api/ai")
    fake_java = FakeJavaClient()
    monkeypatch.setattr(knowledge_tree, "java_client", fake_java)
    monkeypatch.setattr(knowledge_tree, "get_knowledge_tree_ai_service", lambda: FakeService())
    return TestClient(app), fake_java


def parse_sse_lines(text):
    payloads = []
    for line in text.splitlines():
        if line.startswith("data: "):
            payloads.append(json.loads(line.removeprefix("data: ")))
    return payloads


def test_ensure_tree_validates_ticket(monkeypatch):
    client, fake_java = make_client(monkeypatch)

    response = client.get("/api/ai/tree/plan/42/ensure", params={"ticket": "ticket_a"})

    assert response.status_code == 200
    assert fake_java.validated == ["ticket_a"]
    assert response.json()["tree"]["id"] == "tree_a"


def test_node_action_routes_verify_node_ownership(monkeypatch):
    routes = [
        ("/api/ai/tree/tree_a/nodes/node_a/explain", {"ticket": "ticket_a", "message": "解释"}),
        ("/api/ai/tree/tree_a/nodes/node_a/subdivide", {"ticket": "ticket_a", "angle": "按学习顺序"}),
        ("/api/ai/tree/tree_a/nodes/node_a/first-principles", {"ticket": "ticket_a"}),
        ("/api/ai/tree/tree_a/nodes/node_a/quiz", {"ticket": "ticket_a", "plan_id": 42}),
        ("/api/ai/tree/tree_a/nodes/node_a/flashcards", {"ticket": "ticket_a", "plan_id": 42}),
    ]

    for path, params in routes:
        client, fake_java = make_client(monkeypatch)

        response = client.get(path, params=params)

        assert response.status_code == 200
        assert fake_java.verified == [("tree_a", "node_a", 7)]


def test_explain_endpoint_streams_sse(monkeypatch):
    client, fake_java = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/explain",
        params={"ticket": "ticket_a", "message": "解释"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    payloads = parse_sse_lines(response.text)
    assert fake_java.validated == ["ticket_a"]
    assert payloads[0] == {"type": "start", "node_id": "node_a"}
    assert payloads[-1] == {"type": "done"}


def test_subdivide_endpoint_streams_nodes_created(monkeypatch):
    client, _ = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/subdivide",
        params={"ticket": "ticket_a", "angle": "按学习顺序"},
    )

    payloads = parse_sse_lines(response.text)
    assert response.status_code == 200
    assert any(e["type"] == "nodes_created" for e in payloads)
    assert payloads[-1]["type"] == "done"


def test_node_action_rejects_unowned_node_before_streaming(monkeypatch):
    client, fake_java = make_client(monkeypatch)
    fake_java.fail_verify = True

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/explain",
        params={"ticket": "ticket_a", "message": "解释"},
    )

    assert response.status_code == 404
    assert fake_java.verified == [("tree_a", "node_a", 7)]


def test_first_principles_endpoint_streams_nodes_created(monkeypatch):
    client, _ = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/first-principles",
        params={"ticket": "ticket_a"},
    )

    payloads = parse_sse_lines(response.text)
    assert response.status_code == 200
    assert any(e["type"] == "nodes_created" for e in payloads)
    assert payloads[-1]["type"] == "done"


def test_quiz_endpoint_streams_resource_generated(monkeypatch):
    client, fake_java = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/quiz",
        params={"ticket": "ticket_a", "plan_id": 42},
    )

    payloads = parse_sse_lines(response.text)
    assert response.status_code == 200
    assert fake_java.plan_checks == [(42, 7)]
    assert payloads[0]["type"] == "resource_generated"
    assert payloads[0]["resources"] == [{"id": 123, "type": "quiz", "title": "节点练习题"}]
    assert payloads[-1]["type"] == "done"


def test_quiz_endpoint_rejects_plan_tree_mismatch_before_streaming(monkeypatch):
    client, fake_java = make_client(monkeypatch)
    fake_java.plan_tree_id = "tree_b"

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/quiz",
        params={"ticket": "ticket_a", "plan_id": 42},
    )

    assert response.status_code == 404
    assert fake_java.verified == [("tree_a", "node_a", 7)]
    assert fake_java.plan_checks == [(42, 7)]


def test_flashcards_endpoint_streams_flashcards(monkeypatch):
    client, fake_java = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/flashcards",
        params={"ticket": "ticket_a", "plan_id": 42},
    )

    payloads = parse_sse_lines(response.text)
    assert response.status_code == 200
    assert fake_java.plan_checks == [(42, 7)]
    assert payloads[0]["type"] == "flashcards_generated"
    assert payloads[0]["cards"] == [{"question": "Q", "answer": "A", "difficulty": 1}]
    assert payloads[-1]["type"] == "done"
