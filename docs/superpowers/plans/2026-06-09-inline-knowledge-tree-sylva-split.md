# Inline Knowledge Tree Sylva Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the knowledge tree from a separate page into the plan detail page as a right-side view mode, with a Sylva-style split workflow and a tree-shaped plan outline on the left.

**Architecture:** The existing Java knowledge tree remains the source of truth for persisted tree/node data. Python owns AI split workflows over SSE, including subdivision angle suggestions and multi-angle split creation. Vue owns the same-page mode switch, the tree outline, the full-canvas split workspace, and resource-to-node display mapping.

**Tech Stack:** Java Spring Boot + MyBatis Plus, Python FastAPI SSE, Vue 3 Composition API, Pinia, Vitest, pytest.

---

## Product Decisions From Grill Session

- Default `/plan/:id` opens the existing learning/resource mode.
- Clicking the existing knowledge-tree icon switches the current plan detail page into knowledge-tree mode; it does not navigate away.
- In knowledge-tree mode, the original resource detail panel and AI chat panel are hidden together, and the full right area becomes a Sylva-style tree canvas.
- Existing background generation tasks continue; hiding the resource panel must not cancel them.
- Clicking a resource item in the left outline switches back to learning/resource mode and opens that resource.
- The knowledge-tree mode left sidebar becomes a tree-shaped plan outline. It shows the root node, child nodes, and lightweight resource rows under their matching nodes.
- Nodes and resources are visually different: knowledge nodes are primary outline rows; resources are smaller child rows with type labels.
- Tree split operations persist knowledge nodes only. They do not create empty `LearningResource` rows.
- Knowledge tree structure is persisted in knowledge-tree tables. Existing learning/resource mode continues to show real resources only.
- Resource mounting rules: `resource.nodeId` / `resource.moduleData.nodeId` first, node `resourceId` second, title match third, unmatched resources under root in an "未归类资源" group.
- Right-side split interaction mimics `D:\a\Bura\TJ-Sylva-main`: click node split, choose split method, request AI angle suggestions, then multi-angle split, single-angle split, or custom angle split.
- Keep "按知识点拆分", "第一性原理 · 拆到底", AI angle recommendations, multi-angle split, and custom angle split.
- Do not include "先别拆" in Aura because knowledge-tree mode has no chat panel.
- Multi-angle split creates angle grouping nodes, then children under each group.
- Add a stop action for long-running split streams. Closing the EventSource keeps already-saved nodes and stops further client updates.
- First version does not support drag-and-drop reordering.
- Visual design follows Aura's light `navy/sage/white` style; only the interaction pattern is borrowed from Sylva.

---

## File Structure

### Python Backend

- Modify `Python-backend/app/services/knowledge_tree_ai.py`
  - Add `suggest_subdivision_options()`.
  - Add `multi_angle_subdivide()`.
  - Add prompt helpers and normalizers for subdivision options and angle groups.
  - Keep existing `subdivide_node()` and `first_principles()` for single-angle/custom and first-principles streams.
- Modify `Python-backend/app/api/v1/endpoints/knowledge_tree.py`
  - Add JSON endpoint for subdivision options.
  - Add SSE endpoint for multi-angle split.
- Modify `Python-backend/app/schemas/knowledge_tree.py`
  - Add Pydantic event allowance for `subdivision_options` if needed by stream validation.
- Modify `Python-backend/tests/test_knowledge_tree_ai.py`
  - Cover subdivision option normalization and multi-angle group node creation.
- Modify `Python-backend/tests/test_knowledge_tree_endpoints.py`
  - Cover ticket validation, node ownership checks, options endpoint, and multi-angle SSE endpoint.

### Vue Frontend

- Modify `Vue-frontend/src/types/knowledgeTree.ts`
  - Add subdivision option and angle types.
- Modify `Vue-frontend/src/api/knowledgeTree.ts`
  - Add `getTreeSubdivisionOptions()`.
  - Add `streamTreeMultiAngleSubdivide()`.
  - Keep quiz/flashcards API exported for existing code, but remove them from the new tree workspace UI.
- Modify `Vue-frontend/src/api/knowledgeTree.test.ts`
  - Cover new URL construction and `nodes_created` SSE mapping for multi-angle split.
- Modify `Vue-frontend/src/stores/knowledgeTree.ts`
  - Add options loading state and split popover methods.
  - Add multi-angle split stream method.
  - Use existing `stopStream()` for the stop action.
- Modify `Vue-frontend/src/stores/knowledgeTree.test.ts`
  - Cover options loading, multi-angle stream start, stale response guards, and stop behavior.
- Create `Vue-frontend/src/components/tree/useTreePlanOutline.ts`
  - Build left outline rows from knowledge nodes and learning resources.
  - Encapsulate resource mounting rules.
- Create `Vue-frontend/src/components/tree/useTreePlanOutline.test.ts`
  - Unit-test root display, node nesting, resource mounting, title fallback, and unmatched resources.
- Create `Vue-frontend/src/components/tree/KnowledgeTreeOutline.vue`
  - Render left tree-shaped plan outline.
  - Emit `select-node`, `open-resource`, and `toggle-collapse`.
- Modify `Vue-frontend/src/components/tree/KnowledgeTreeNode.vue`
  - Remove chat/explain action from the node card UI.
  - Keep one structural `拆分` entry that opens the popover.
- Modify `Vue-frontend/src/components/tree/KnowledgeTreeCanvas.vue`
  - Make the canvas feel closer to Sylva: full area, subtle grid, bottom zoom toolbar, node split event.
  - Keep pan/zoom/collapse behavior.
- Create `Vue-frontend/src/components/tree/TreeSubdividePopover.vue`
  - Implement two-step Sylva-style split flow.
  - No "先别拆" branch.
  - Shows loading and error states.
- Modify `Vue-frontend/src/views/PlanDetailView.vue`
  - Add `view=tree` mode support.
  - In tree mode, left sidebar renders `KnowledgeTreeOutline`; right side renders the tree canvas and popover.
  - Existing resource panel, divider, and `PlanChatPanel` render only in learning mode.
  - Clicking a resource outline row exits tree mode and opens the resource.
- Modify `Vue-frontend/src/config/routeComponents.ts`
  - Change `/plan/:planId/tree` into a compatibility redirect to `/plan/:planId?view=tree`.
- Modify `Vue-frontend/src/components/layout/AppSidebar.vue` only if the route-name active check fails after redirect.

---

## Task 1: Python Subdivision Options API

**Files:**
- Modify: `Python-backend/app/services/knowledge_tree_ai.py`
- Modify: `Python-backend/app/api/v1/endpoints/knowledge_tree.py`
- Modify: `Python-backend/tests/test_knowledge_tree_ai.py`
- Modify: `Python-backend/tests/test_knowledge_tree_endpoints.py`

- [ ] **Step 1: Add failing service tests for subdivision options**

Append these tests to `Python-backend/tests/test_knowledge_tree_ai.py`:

```python
def test_suggest_subdivision_options_normalizes_llm_output():
    asyncio.run(_test_suggest_subdivision_options_normalizes_llm_output())


async def _test_suggest_subdivision_options_normalizes_llm_output():
    client = FakeJavaClient()
    service = KnowledgeTreeAiService(java_client=client, retriever=FakeRetriever(), llm=FakeJsonLlm({
        "options": [
            {"angle": "by_concept", "label": "按概念拆", "rationale": "先把核心概念分开"},
            {"angle": "by_flow", "label": "按流程拆", "rationale": "再按学习顺序推进"},
            {"label": "按错误拆", "rationale": "覆盖常见误区"},
            {"angle": "", "label": "", "rationale": "空项应被过滤"}
        ],
        "caution": {"label": "先别拆", "rationale": "Aura UI 不使用这个分支"}
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
```

- [ ] **Step 2: Run the new service test and verify it fails**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py::test_suggest_subdivision_options_normalizes_llm_output -q
```

Expected: `FAILED` because `KnowledgeTreeAiService` has no `suggest_subdivision_options`.

- [ ] **Step 3: Implement subdivision option generation**

In `Python-backend/app/services/knowledge_tree_ai.py`, add this public method inside `KnowledgeTreeAiService` after `first_principles()`:

```python
    async def suggest_subdivision_options(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
    ) -> Dict[str, Any]:
        search_results, context_chunks = await self._search("知识点拆分角度")
        result = await self._chat_json([
            {"role": "system", "content": self._subdivision_options_json_system_prompt()},
            {"role": "user", "content": self._subdivision_options_prompt(node_id, context_chunks)},
        ])
        return {
            "tree_id": tree_id,
            "node_id": node_id,
            "options": self._normalize_subdivision_options(result),
            "search_results": search_results,
        }
```

Add these helpers near the existing prompt/normalizer helpers:

```python
    def _subdivision_options_json_system_prompt(self) -> str:
        return (
            "严格输出 JSON："
            "{\"options\":[{\"angle\":\"stable_key\",\"label\":\"按概念拆\","
            "\"rationale\":\"为什么这个角度适合当前节点\"}]}。"
            "只返回 2 到 4 个拆分角度，不要返回 caution/先别拆。"
        )

    def _subdivision_options_prompt(self, node_id: str, context_chunks: List[Dict[str, Any]]) -> str:
        return (
            f"请为知识树节点 node_id={node_id} 推荐 3 个适合继续拆分的角度。"
            "角度必须能生成并列的学习子节点，避免泛泛而谈。"
            f"\n参考资料：\n{self._context_text(context_chunks)}"
        )

    def _normalize_subdivision_options(self, result: Any) -> List[Dict[str, str]]:
        raw_options = result.get("options", []) if isinstance(result, dict) else []
        normalized: List[Dict[str, str]] = []
        for item in raw_options:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("title") or item.get("angle") or "").strip()
            angle = str(item.get("angle") or label).strip()
            rationale = str(item.get("rationale") or item.get("reason") or item.get("summary") or "").strip()
            if not label or not angle:
                continue
            normalized.append({
                "angle": angle[:60],
                "label": label[:40],
                "rationale": rationale[:180],
            })
            if len(normalized) >= 4:
                break
        if normalized:
            return normalized
        return [
            {"angle": "按概念拆", "label": "按概念拆", "rationale": "把抽象概念拆成可逐个理解的知识点。"},
            {"angle": "按学习顺序拆", "label": "按学习顺序拆", "rationale": "按先易后难的路径组织学习。"},
            {"angle": "按应用场景拆", "label": "按应用场景拆", "rationale": "把知识放到实际使用场景中理解。"},
        ]
```

- [ ] **Step 4: Run the service test and verify it passes**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py::test_suggest_subdivision_options_normalizes_llm_output -q
```

Expected: `1 passed`.

- [ ] **Step 5: Add failing endpoint test for subdivision options**

In `Python-backend/tests/test_knowledge_tree_endpoints.py`, add this method to `FakeService`:

```python
    async def suggest_subdivision_options(self, **kwargs):
        return {
            "tree_id": kwargs["tree_id"],
            "node_id": kwargs["node_id"],
            "options": [{"angle": "by_concept", "label": "按概念拆", "rationale": "先拆概念"}],
        }
```

Then append this test:

```python
def test_subdivision_options_endpoint_validates_ticket_and_node(monkeypatch):
    client, fake_java = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/subdivision-options",
        params={"ticket": "ticket_a"},
    )

    assert response.status_code == 200
    assert fake_java.validated == ["ticket_a"]
    assert fake_java.verified == [("tree_a", "node_a", 7)]
    assert response.json()["options"] == [
        {"angle": "by_concept", "label": "按概念拆", "rationale": "先拆概念"}
    ]
```

- [ ] **Step 6: Run endpoint test and verify it fails**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_endpoints.py::test_subdivision_options_endpoint_validates_ticket_and_node -q
```

Expected: `404 Not Found` or `AttributeError` because the route does not exist.

- [ ] **Step 7: Implement subdivision options route**

In `Python-backend/app/api/v1/endpoints/knowledge_tree.py`, add this route after `subdivide_node()`:

```python
@router.get("/tree/{tree_id}/nodes/{node_id}/subdivision-options")
async def subdivision_options(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return await service.suggest_subdivision_options(
        user_id=user_id,
        tree_id=tree_id,
        node_id=node_id,
    )
```

- [ ] **Step 8: Run endpoint test and verify it passes**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_endpoints.py::test_subdivision_options_endpoint_validates_ticket_and_node -q
```

Expected: `1 passed`.

- [ ] **Step 9: Run targeted Python tests**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py tests/test_knowledge_tree_endpoints.py -q
```

Expected: all targeted tests pass.

- [ ] **Step 10: Commit**

```bash
git add Python-backend/app/services/knowledge_tree_ai.py Python-backend/app/api/v1/endpoints/knowledge_tree.py Python-backend/tests/test_knowledge_tree_ai.py Python-backend/tests/test_knowledge_tree_endpoints.py
git commit -m "feat: add knowledge tree subdivision options"
```

---

## Task 2: Python Multi-Angle Split API

**Files:**
- Modify: `Python-backend/app/services/knowledge_tree_ai.py`
- Modify: `Python-backend/app/api/v1/endpoints/knowledge_tree.py`
- Modify: `Python-backend/tests/test_knowledge_tree_ai.py`
- Modify: `Python-backend/tests/test_knowledge_tree_endpoints.py`

- [ ] **Step 1: Add failing service test for grouped multi-angle split**

Append this test to `Python-backend/tests/test_knowledge_tree_ai.py`:

```python
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
                    {"title": "类型是什么", "summary": "理解类型的约束"}
                ]
            },
            {
                "angle": "by_flow",
                "label": "按流程拆",
                "children": [
                    {"title": "赋值", "summary": "把值绑定到变量"}
                ]
            }
        ]
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
```

- [ ] **Step 2: Run service test and verify it fails**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py::test_multi_angle_subdivide_creates_group_nodes_and_children -q
```

Expected: `FAILED` because `multi_angle_subdivide` is missing.

- [ ] **Step 3: Implement multi-angle split service**

In `Python-backend/app/services/knowledge_tree_ai.py`, add this method after `subdivide_node()`:

```python
    async def multi_angle_subdivide(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        angles: List[Dict[str, str]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            normalized_angles = self._normalize_requested_angles(angles)
            if not normalized_angles:
                yield {"type": "error", "content": "请选择至少一个拆分角度"}
                return
            search_results, context_chunks = await self._search(" ".join(a["label"] for a in normalized_angles))
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": self._multi_angle_json_system_prompt()},
                {"role": "user", "content": self._multi_angle_prompt(node_id, normalized_angles, context_chunks)},
            ])
            groups = self._normalize_angle_groups(result, normalized_angles)
            nodes: List[Dict[str, Any]] = []
            for group_index, group in enumerate(groups):
                group_node = self.java_client.create_tree_node({
                    "treeId": tree_id,
                    "parentId": node_id,
                    "title": group["label"],
                    "summary": group.get("rationale", ""),
                    "content": "",
                    "status": "pending",
                    "importance": 2,
                    "relevanceScore": 2,
                    "difficulty": 2,
                    "sortOrder": group_index,
                    "collapsed": False,
                })
                nodes.append(group_node)
                group_node_id = str(group_node.get("id"))
                for child_index, child in enumerate(group["children"]):
                    payload = self._child_payload(tree_id, group_node_id, child, child_index)
                    nodes.append(self.java_client.create_tree_node(payload))
            yield {"type": "nodes_created", "nodes": nodes}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("multi_angle_subdivide failed")
            yield {"type": "error", "content": str(exc)}
```

Add these helpers near the other helper methods:

```python
    def _normalize_requested_angles(self, angles: List[Dict[str, str]]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for item in angles[:4]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("angle") or "").strip()
            angle = str(item.get("angle") or label).strip()
            rationale = str(item.get("rationale") or "").strip()
            if not label or not angle:
                continue
            normalized.append({"angle": angle[:60], "label": label[:40], "rationale": rationale[:180]})
        return normalized

    def _multi_angle_json_system_prompt(self) -> str:
        return (
            "严格输出 JSON：{\"groups\":[{\"angle\":\"by_concept\",\"label\":\"按概念拆\","
            "\"rationale\":\"拆分理由\",\"children\":[{\"title\":\"子知识点\",\"summary\":\"说明\","
            "\"importance\":3,\"difficulty\":2}]}]}。"
            "每个 group 对应用户给定的一个角度，每组 children 生成 2 到 5 个。"
        )

    def _multi_angle_prompt(
        self,
        node_id: str,
        angles: List[Dict[str, str]],
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        return (
            f"请把知识树节点 node_id={node_id} 按这些角度一次性拆开："
            f"{json.dumps(angles, ensure_ascii=False)}。"
            "每个角度先形成一个分组节点，再在分组下生成具体可学习子节点。"
            f"\n参考资料：\n{self._context_text(context_chunks)}"
        )

    def _normalize_angle_groups(
        self,
        result: Any,
        requested_angles: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        raw_groups = result.get("groups", []) if isinstance(result, dict) else []
        groups_by_angle = {}
        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            key = str(group.get("angle") or group.get("label") or "").strip()
            children = self._coerce_children({"children": group.get("children", [])})
            if key and children:
                groups_by_angle[key] = {
                    "angle": key,
                    "label": str(group.get("label") or key).strip()[:40],
                    "rationale": str(group.get("rationale") or "").strip()[:180],
                    "children": children,
                }
        normalized: List[Dict[str, Any]] = []
        for requested in requested_angles:
            group = groups_by_angle.get(requested["angle"]) or groups_by_angle.get(requested["label"])
            if group:
                normalized.append(group)
                continue
            normalized.append({
                "angle": requested["angle"],
                "label": requested["label"],
                "rationale": requested.get("rationale", ""),
                "children": [
                    {"title": f"{requested['label']}要点 1", "summary": "从这个角度继续细化学习。"},
                    {"title": f"{requested['label']}要点 2", "summary": "补足这个角度下的关键知识。"},
                ],
            })
        return normalized
```

- [ ] **Step 4: Run service test and verify it passes**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py::test_multi_angle_subdivide_creates_group_nodes_and_children -q
```

Expected: `1 passed`.

- [ ] **Step 5: Add failing endpoint test for multi-angle SSE**

In `Python-backend/tests/test_knowledge_tree_endpoints.py`, add this method to `FakeService`:

```python
    async def multi_angle_subdivide(self, **kwargs):
        yield {"type": "start", "node_id": kwargs["node_id"]}
        yield {
            "type": "nodes_created",
            "nodes": [
                {"id": "group_1", "title": "按概念拆", "parentId": kwargs["node_id"]},
                {"id": "child_1", "title": "变量是什么", "parentId": "group_1"},
            ],
        }
        yield {"type": "done"}
```

Append this test:

```python
def test_multi_angle_endpoint_streams_grouped_nodes(monkeypatch):
    client, fake_java = make_client(monkeypatch)

    response = client.get(
        "/api/ai/tree/tree_a/nodes/node_a/multi-angle-subdivide",
        params={
            "ticket": "ticket_a",
            "angles": json.dumps([
                {"angle": "by_concept", "label": "按概念拆", "rationale": "先拆概念"}
            ], ensure_ascii=False),
        },
    )

    payloads = parse_sse_lines(response.text)
    assert response.status_code == 200
    assert fake_java.verified == [("tree_a", "node_a", 7)]
    assert payloads[1]["type"] == "nodes_created"
    assert payloads[1]["nodes"][0]["title"] == "按概念拆"
    assert payloads[-1]["type"] == "done"
```

- [ ] **Step 6: Run endpoint test and verify it fails**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_endpoints.py::test_multi_angle_endpoint_streams_grouped_nodes -q
```

Expected: `404 Not Found`.

- [ ] **Step 7: Implement multi-angle endpoint**

In `Python-backend/app/api/v1/endpoints/knowledge_tree.py`, import `json` at the top:

```python
import json
```

Add this route after `subdivision_options()`:

```python
@router.get("/tree/{tree_id}/nodes/{node_id}/multi-angle-subdivide")
async def multi_angle_subdivide_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    angles: str = Query("[]"),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    try:
        parsed_angles = json.loads(angles)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid angles json") from exc
    if not isinstance(parsed_angles, list):
        raise HTTPException(status_code=400, detail="angles must be a list")
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.multi_angle_subdivide(
            user_id=user_id,
            tree_id=tree_id,
            node_id=node_id,
            angles=parsed_angles,
        )),
        media_type="text/event-stream",
    )
```

- [ ] **Step 8: Run endpoint test and targeted Python tests**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py tests/test_knowledge_tree_endpoints.py -q
```

Expected: all targeted tests pass.

- [ ] **Step 9: Commit**

```bash
git add Python-backend/app/services/knowledge_tree_ai.py Python-backend/app/api/v1/endpoints/knowledge_tree.py Python-backend/tests/test_knowledge_tree_ai.py Python-backend/tests/test_knowledge_tree_endpoints.py
git commit -m "feat: add knowledge tree multi angle split"
```

---

## Task 3: Frontend API and Store Support for Sylva Split

**Files:**
- Modify: `Vue-frontend/src/types/knowledgeTree.ts`
- Modify: `Vue-frontend/src/api/knowledgeTree.ts`
- Modify: `Vue-frontend/src/api/knowledgeTree.test.ts`
- Modify: `Vue-frontend/src/stores/knowledgeTree.ts`
- Modify: `Vue-frontend/src/stores/knowledgeTree.test.ts`

- [ ] **Step 1: Add failing API tests**

Modify `Vue-frontend/src/api/knowledgeTree.test.ts` imports:

```ts
import {
  getTreeSubdivisionOptions,
  streamTreeExplain,
  streamTreeFlashcards,
  streamTreeMultiAngleSubdivide,
  streamTreeQuiz,
} from './knowledgeTree'
```

Extend the request mock to include `get`:

```ts
const requestGet = vi.fn()

vi.mock('@/api/request', () => ({
  default: {
    get: requestGet,
  },
  PYTHON_AI_BASE: 'http://localhost:8002',
}))
```

Append these tests:

```ts
it('requests subdivision options from the Python AI base with ticket auth', async () => {
  requestGet.mockResolvedValueOnce({ options: [] })

  await getTreeSubdivisionOptions('ticket_1', 'tree_1', 'node_root')

  expect(requestGet).toHaveBeenCalledWith(
    'http://localhost:8002/api/ai/tree/tree_1/nodes/node_root/subdivision-options',
    { params: { ticket: 'ticket_1' } },
  )
})

it('streams multi-angle subdivision with encoded angles', () => {
  const onNodes = vi.fn()

  streamTreeMultiAngleSubdivide('ticket_1', 'tree_1', 'node_root', [
    { angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' },
  ], { onNodes })

  const source = FakeEventSource.instances[0]
  expect(decodeURIComponent(source.url)).toContain('/api/ai/tree/tree_1/nodes/node_root/multi-angle-subdivide')
  expect(decodeURIComponent(source.url)).toContain('"label":"按概念拆"')

  source.emit('nodes_created', {
    type: 'nodes_created',
    nodes: [{ id: 'node_child', treeId: 'tree_1', parentId: 'node_root', title: 'Child' }],
  })

  expect(onNodes).toHaveBeenCalledWith([
    { id: 'node_child', treeId: 'tree_1', parentId: 'node_root', title: 'Child' },
  ])
})
```

- [ ] **Step 2: Run API tests and verify they fail**

Run:

```bash
cd Vue-frontend
npm test -- src/api/knowledgeTree.test.ts
```

Expected: tests fail because the new exports are missing.

- [ ] **Step 3: Add frontend types**

In `Vue-frontend/src/types/knowledgeTree.ts`, add:

```ts
export interface TreeSubdivisionOption {
  angle: string
  label: string
  rationale: string
}

export interface TreeSubdivisionOptionsResponse {
  tree_id?: string
  node_id: string
  options: TreeSubdivisionOption[]
  search_results?: unknown[]
}
```

- [ ] **Step 4: Add API functions**

In `Vue-frontend/src/api/knowledgeTree.ts`, extend imports:

```ts
  TreeSubdivisionOption,
  TreeSubdivisionOptionsResponse,
```

Add this function after `getKnowledgeNodeMessages()`:

```ts
export function getTreeSubdivisionOptions(
  ticket: string,
  treeId: string,
  nodeId: string,
) {
  return request.get<TreeSubdivisionOptionsResponse>(
    `${PYTHON_AI_BASE}/api/ai/tree/${treeId}/nodes/${nodeId}/subdivision-options`,
    { params: { ticket } },
  )
}
```

Add this SSE function after `streamTreeSubdivide()`:

```ts
export function streamTreeMultiAngleSubdivide(
  ticket: string,
  treeId: string,
  nodeId: string,
  angles: TreeSubdivisionOption[],
  handlers: TreeSseHandlers,
): EventSource {
  return createTreeSse(
    `/api/ai/tree/${treeId}/nodes/${nodeId}/multi-angle-subdivide`,
    { ticket, angles: JSON.stringify(angles) },
    handlers,
  )
}
```

- [ ] **Step 5: Run API tests and verify they pass**

Run:

```bash
cd Vue-frontend
npm test -- src/api/knowledgeTree.test.ts
```

Expected: API tests pass.

- [ ] **Step 6: Add failing store tests**

In `Vue-frontend/src/stores/knowledgeTree.test.ts`, extend the mocked imports with:

```ts
  getTreeSubdivisionOptions,
  streamTreeMultiAngleSubdivide,
```

Extend the `vi.mock('@/api/knowledgeTree')` object:

```ts
  getTreeSubdivisionOptions: vi.fn(),
  streamTreeMultiAngleSubdivide: vi.fn(),
```

Append these tests:

```ts
it('loads subdivision options for the current node with a ticket', async () => {
  vi.mocked(getTreeSubdivisionOptions).mockResolvedValueOnce({
    options: [{ angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' }],
  })
  const store = useKnowledgeTreeStore()
  await store.loadByPlan(42)

  const options = await store.loadSubdivisionOptionsCurrent()

  expect(issueTicket).toHaveBeenCalled()
  expect(getTreeSubdivisionOptions).toHaveBeenCalledWith('ticket_1', 'tree_1', 'node_root')
  expect(options).toEqual([{ angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' }])
  expect(store.subdivisionOptionsLoading).toBe(false)
})

it('starts multi-angle split stream and merges created nodes', async () => {
  const source = new FakeEventSource()
  vi.mocked(streamTreeMultiAngleSubdivide).mockImplementation((ticket, treeId, nodeId, angles, handlers) => {
    handlers.onNodes?.([{ id: 'group_1', treeId, parentId: nodeId, title: angles[0].label } as KnowledgeNode])
    handlers.onDone?.()
    return source as unknown as EventSource
  })
  const store = useKnowledgeTreeStore()
  await store.loadByPlan(42)

  await store.multiAngleSubdivideCurrent([
    { angle: 'by_concept', label: '按概念拆', rationale: '先拆概念' },
  ])

  expect(streamTreeMultiAngleSubdivide).toHaveBeenCalled()
  expect(store.nodes.some(node => node.id === 'group_1')).toBe(true)
  expect(store.loading).toBe(false)
})
```

- [ ] **Step 7: Run store tests and verify they fail**

Run:

```bash
cd Vue-frontend
npm test -- src/stores/knowledgeTree.test.ts
```

Expected: tests fail because store fields/methods are missing.

- [ ] **Step 8: Implement store state and methods**

In `Vue-frontend/src/stores/knowledgeTree.ts`, extend imports:

```ts
  getTreeSubdivisionOptions,
  streamTreeMultiAngleSubdivide,
```

Extend type imports:

```ts
  TreeSubdivisionOption,
```

Add state near `loading`:

```ts
  const subdivisionOptionsLoading = ref(false)
  const subdivisionOptionsError = ref('')
```

Add methods after `subdivideCurrent()`:

```ts
  async function loadSubdivisionOptionsCurrent(): Promise<TreeSubdivisionOption[]> {
    if (!tree.value || !currentNodeId.value) return []
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    const token = nextSelectionToken()
    subdivisionOptionsLoading.value = true
    subdivisionOptionsError.value = ''
    try {
      const ticketRes = await issueTicket()
      if (!isCurrentSelection(token) || currentNodeId.value !== nodeId) return []
      const res = await getTreeSubdivisionOptions(ticketRes.data.ticket, treeId, nodeId)
      if (!isCurrentSelection(token) || currentNodeId.value !== nodeId) return []
      return res.options || []
    } catch (e) {
      if (isCurrentSelection(token)) {
        subdivisionOptionsError.value = getErrorMessage(e)
      }
      return []
    } finally {
      if (isCurrentSelection(token)) {
        subdivisionOptionsLoading.value = false
      }
    }
  }

  async function multiAngleSubdivideCurrent(angles: TreeSubdivisionOption[]) {
    if (!tree.value || !currentNodeId.value || angles.length === 0) return
    const treeId = tree.value.id
    const nodeId = currentNodeId.value
    await startStream(nodeId, (ticket, handlers) => streamTreeMultiAngleSubdivide(
      ticket,
      treeId,
      nodeId,
      angles,
      handlers,
    ))
  }
```

Return the new state and methods:

```ts
    subdivisionOptionsLoading,
    subdivisionOptionsError,
    loadSubdivisionOptionsCurrent,
    multiAngleSubdivideCurrent,
```

- [ ] **Step 9: Run store tests and full Vue tests**

Run:

```bash
cd Vue-frontend
npm test -- src/stores/knowledgeTree.test.ts
npm test -- src/api/knowledgeTree.test.ts
```

Expected: both targeted test files pass.

- [ ] **Step 10: Commit**

```bash
git add Vue-frontend/src/types/knowledgeTree.ts Vue-frontend/src/api/knowledgeTree.ts Vue-frontend/src/api/knowledgeTree.test.ts Vue-frontend/src/stores/knowledgeTree.ts Vue-frontend/src/stores/knowledgeTree.test.ts
git commit -m "feat: add sylva split frontend state"
```

---

## Task 4: Tree Plan Outline Data Model

**Files:**
- Create: `Vue-frontend/src/components/tree/useTreePlanOutline.ts`
- Create: `Vue-frontend/src/components/tree/useTreePlanOutline.test.ts`

- [ ] **Step 1: Write failing outline tests**

Create `Vue-frontend/src/components/tree/useTreePlanOutline.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { buildTreePlanOutline } from './useTreePlanOutline'
import type { KnowledgeNode } from '@/types/knowledgeTree'
import type { LearningResource } from '@/types/plan'

const nodes: KnowledgeNode[] = [
  { id: 'root', treeId: 'tree_1', parentId: null, title: 'Python 基础学习', sortOrder: 0 },
  { id: 'env', treeId: 'tree_1', parentId: 'root', title: 'Python 环境搭建与初体验', sortOrder: 1 },
  { id: 'vars', treeId: 'tree_1', parentId: 'root', title: '变量、数据类型与基本操作', sortOrder: 2 },
]

function resource(partial: Partial<LearningResource>): LearningResource {
  return {
    id: partial.id || 1,
    planId: 42,
    parentId: null,
    moduleOrder: partial.moduleOrder || 1,
    moduleType: partial.moduleType || 'text',
    moduleData: partial.moduleData || {},
    status: partial.status ?? 2,
    storagePath: null,
    generatedByAgent: null,
    version: 1,
    createdAt: '',
    updatedAt: '',
    ...partial,
  } as LearningResource
}

describe('buildTreePlanOutline', () => {
  it('shows the root node and nested child nodes', () => {
    const outline = buildTreePlanOutline(nodes, [], 'root')

    expect(outline[0].kind).toBe('node')
    expect(outline[0].title).toBe('Python 基础学习')
    expect(outline[0].children.filter(item => item.kind === 'node').map(item => item.title)).toEqual([
      'Python 环境搭建与初体验',
      '变量、数据类型与基本操作',
    ])
  })

  it('mounts resources by moduleData nodeId and node resourceId', () => {
    const outline = buildTreePlanOutline([
      ...nodes,
      { id: 'linked', treeId: 'tree_1', parentId: 'root', title: '直接关联节点', resourceId: 77, sortOrder: 3 },
    ], [
      resource({ id: 11, moduleType: 'text', moduleData: { nodeId: 'root', title: '基础练习' } }),
      resource({ id: 22, moduleType: 'animation', moduleData: { nodeId: 'vars', title: '变量演示' } }),
      resource({ id: 77, moduleType: 'quiz', moduleData: { title: '直接题目' } }),
    ], 'root')

    expect(outline[0].children[0]).toMatchObject({ kind: 'resource', title: '基础练习', resourceId: 11 })
    const vars = outline[0].children.find(item => item.kind === 'node' && item.nodeId === 'vars')
    expect(vars?.children[0]).toMatchObject({ kind: 'resource', title: '变量演示', resourceId: 22 })
    const linked = outline[0].children.find(item => item.kind === 'node' && item.nodeId === 'linked')
    expect(linked?.children[0]).toMatchObject({ kind: 'resource', title: '直接题目', resourceId: 77 })
  })

  it('falls back to title matching and unmatched resources under root', () => {
    const outline = buildTreePlanOutline(nodes, [
      resource({ id: 33, moduleType: 'text', moduleData: { module_title: 'Python 环境搭建与初体验', title: '环境搭建说明' } }),
      resource({ id: 44, moduleType: 'video', moduleData: { title: '外部补充视频' } }),
    ], 'root')

    const env = outline[0].children.find(item => item.kind === 'node' && item.nodeId === 'env')
    expect(env?.children[0]).toMatchObject({ kind: 'resource', title: '环境搭建说明', resourceId: 33 })
    const uncategorized = outline[0].children.find(item => item.kind === 'group' && item.title === '未归类资源')
    expect(uncategorized?.children[0]).toMatchObject({ kind: 'resource', title: '外部补充视频', resourceId: 44 })
  })
})
```

- [ ] **Step 2: Run outline tests and verify they fail**

Run:

```bash
cd Vue-frontend
npm test -- src/components/tree/useTreePlanOutline.test.ts
```

Expected: test file fails because `useTreePlanOutline.ts` does not exist.

- [ ] **Step 3: Implement outline builder**

Create `Vue-frontend/src/components/tree/useTreePlanOutline.ts`:

```ts
import type { KnowledgeNode } from '@/types/knowledgeTree'
import type { LearningResource } from '@/types/plan'

export type TreePlanOutlineItem =
  | TreePlanNodeItem
  | TreePlanResourceItem
  | TreePlanGroupItem

export interface TreePlanNodeItem {
  kind: 'node'
  id: string
  nodeId: string
  title: string
  summary: string
  depth: number
  collapsed: boolean
  children: TreePlanOutlineItem[]
}

export interface TreePlanResourceItem {
  kind: 'resource'
  id: string
  resourceId: number
  title: string
  resourceType: string
  depth: number
  children: []
}

export interface TreePlanGroupItem {
  kind: 'group'
  id: string
  title: string
  depth: number
  children: TreePlanResourceItem[]
}

export function buildTreePlanOutline(
  nodes: KnowledgeNode[],
  resources: LearningResource[],
  rootNodeId: string | null,
): TreePlanOutlineItem[] {
  if (!rootNodeId) return []
  const nodeById = new Map(nodes.map(node => [node.id, node]))
  const root = nodeById.get(rootNodeId)
  if (!root) return []

  const childrenByParent = new Map<string, KnowledgeNode[]>()
  for (const node of nodes) {
    if (!node.parentId) continue
    const siblings = childrenByParent.get(node.parentId) || []
    siblings.push(node)
    childrenByParent.set(node.parentId, siblings)
  }
  for (const siblings of childrenByParent.values()) {
    siblings.sort(compareNodes)
  }

  const mountedResourceIds = new Set<number>()
  const resourcesByNodeId = mountResources(nodes, resources, mountedResourceIds)

  function toNodeItem(node: KnowledgeNode, depth: number): TreePlanNodeItem {
    const childItems = (childrenByParent.get(node.id) || []).map(child => toNodeItem(child, depth + 1))
    const resourceItems = (resourcesByNodeId.get(node.id) || []).map(resource => toResourceItem(resource, depth + 1))
    return {
      kind: 'node',
      id: `node:${node.id}`,
      nodeId: node.id,
      title: node.title || '未命名节点',
      summary: node.summary || '',
      depth,
      collapsed: Boolean(node.collapsed),
      children: [...resourceItems, ...childItems],
    }
  }

  const rootItem = toNodeItem(root, 0)
  const unmatched = resources
    .filter(resource => resource.id != null && !mountedResourceIds.has(resource.id))
    .map(resource => toResourceItem(resource, 1))

  if (unmatched.length) {
    rootItem.children.push({
      kind: 'group',
      id: 'group:uncategorized',
      title: '未归类资源',
      depth: 1,
      children: unmatched,
    })
  }

  return [rootItem]
}

function mountResources(
  nodes: KnowledgeNode[],
  resources: LearningResource[],
  mountedResourceIds: Set<number>,
) {
  const result = new Map<string, LearningResource[]>()
  const nodeById = new Map(nodes.map(node => [node.id, node]))
  const nodeByResourceId = new Map<number, string>()
  const nodeByTitle = new Map<string, string>()

  for (const node of nodes) {
    if (node.resourceId != null) nodeByResourceId.set(node.resourceId, node.id)
    if (node.title) nodeByTitle.set(normalizeTitle(node.title), node.id)
  }

  for (const resource of resources) {
    const nodeId = resourceNodeId(resource)
      || (resource.id != null ? nodeByResourceId.get(resource.id) : undefined)
      || titleMatchedNodeId(resource, nodeByTitle)
    if (!nodeId || !nodeById.has(nodeId) || resource.id == null) continue
    const list = result.get(nodeId) || []
    list.push(resource)
    result.set(nodeId, list)
    mountedResourceIds.add(resource.id)
  }

  return result
}

function resourceNodeId(resource: LearningResource) {
  const data = resource.moduleData || {}
  return (resource as LearningResource & { nodeId?: string }).nodeId
    || data.nodeId
    || data.node_id
    || null
}

function titleMatchedNodeId(resource: LearningResource, nodeByTitle: Map<string, string>) {
  const data = resource.moduleData || {}
  const candidates = [
    data.module_title,
    data.moduleTitle,
    data.title,
  ]
  for (const candidate of candidates) {
    const nodeId = nodeByTitle.get(normalizeTitle(String(candidate || '')))
    if (nodeId) return nodeId
  }
  return undefined
}

function toResourceItem(resource: LearningResource, depth: number): TreePlanResourceItem {
  return {
    kind: 'resource',
    id: `resource:${resource.id}`,
    resourceId: resource.id,
    title: resource.moduleData?.title || resource.moduleData?.module_title || `资源 ${resource.id}`,
    resourceType: resource.moduleType,
    depth,
    children: [],
  }
}

function compareNodes(a: KnowledgeNode, b: KnowledgeNode) {
  const sortDelta = (a.sortOrder ?? 0) - (b.sortOrder ?? 0)
  if (sortDelta !== 0) return sortDelta
  return a.id.localeCompare(b.id)
}

function normalizeTitle(value: string) {
  return value.replace(/\s+/g, '').trim().toLowerCase()
}
```

- [ ] **Step 4: Run outline tests and verify they pass**

Run:

```bash
cd Vue-frontend
npm test -- src/components/tree/useTreePlanOutline.test.ts
```

Expected: all outline tests pass.

- [ ] **Step 5: Commit**

```bash
git add Vue-frontend/src/components/tree/useTreePlanOutline.ts Vue-frontend/src/components/tree/useTreePlanOutline.test.ts
git commit -m "feat: add knowledge tree plan outline model"
```

---

## Task 5: Left Tree Plan Outline UI

**Files:**
- Create: `Vue-frontend/src/components/tree/KnowledgeTreeOutline.vue`
- Modify: `Vue-frontend/src/views/PlanDetailView.vue`

- [ ] **Step 1: Create outline component**

Create `Vue-frontend/src/components/tree/KnowledgeTreeOutline.vue`:

```vue
<template>
  <div class="h-full overflow-y-auto p-3">
    <div v-if="items.length === 0" class="py-8 text-center text-sm text-navy-300">
      暂无知识树节点
    </div>
    <div v-else class="space-y-1">
      <OutlineRow
        v-for="item in items"
        :key="item.id"
        :item="item"
        :selected-node-id="selectedNodeId"
        :type-labels="typeLabels"
        @select-node="$emit('select-node', $event)"
        @open-resource="$emit('open-resource', $event)"
        @toggle-collapse="$emit('toggle-collapse', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h } from 'vue'
import type { PropType } from 'vue'
import type { TreePlanOutlineItem } from './useTreePlanOutline'

defineProps<{
  items: TreePlanOutlineItem[]
  selectedNodeId: string | null
  typeLabels: Record<string, string>
}>()

defineEmits<{
  'select-node': [nodeId: string]
  'open-resource': [resourceId: number]
  'toggle-collapse': [nodeId: string]
}>()

const OutlineRow = defineComponent({
  name: 'OutlineRow',
  props: {
    item: { type: Object as PropType<TreePlanOutlineItem>, required: true },
    selectedNodeId: { type: String as PropType<string | null>, default: null },
    typeLabels: { type: Object as PropType<Record<string, string>>, required: true },
  },
  emits: ['select-node', 'open-resource', 'toggle-collapse'],
  setup(props, { emit }) {
    return () => {
      const item = props.item
      const paddingLeft = `${Math.min(item.depth, 6) * 14}px`
      if (item.kind === 'resource') {
        return h('button', {
          class: 'outline-resource-row',
          style: { paddingLeft },
          title: item.title,
          onClick: () => emit('open-resource', item.resourceId),
        }, [
          h('span', { class: 'outline-resource-type' }, props.typeLabels[item.resourceType] || item.resourceType),
          h('span', { class: 'truncate' }, item.title),
        ])
      }

      if (item.kind === 'group') {
        return h('div', { class: 'space-y-1' }, [
          h('div', { class: 'outline-group-row', style: { paddingLeft } }, item.title),
          ...item.children.map(child => h(OutlineRow, {
            key: child.id,
            item: child,
            selectedNodeId: props.selectedNodeId,
            typeLabels: props.typeLabels,
            onSelectNode: (nodeId: string) => emit('select-node', nodeId),
            onOpenResource: (resourceId: number) => emit('open-resource', resourceId),
            onToggleCollapse: (nodeId: string) => emit('toggle-collapse', nodeId),
          })),
        ])
      }

      const selected = item.nodeId === props.selectedNodeId
      return h('div', { class: 'space-y-1' }, [
        h('div', {
          class: ['outline-node-row', selected ? 'outline-node-row--selected' : ''],
          style: { paddingLeft },
          title: item.summary || item.title,
        }, [
          h('button', {
            class: ['outline-collapse', item.children.length ? '' : 'outline-collapse--empty'],
            disabled: item.children.length === 0,
            title: item.collapsed ? '展开' : '收起',
            onClick: (event: MouseEvent) => {
              event.stopPropagation()
              emit('toggle-collapse', item.nodeId)
            },
          }, item.children.length ? (item.collapsed ? '>' : 'v') : ''),
          h('button', {
            class: 'min-w-0 flex-1 truncate text-left',
            onClick: () => emit('select-node', item.nodeId),
          }, item.title),
        ]),
        ...(item.collapsed ? [] : item.children.map(child => h(OutlineRow, {
          key: child.id,
          item: child,
          selectedNodeId: props.selectedNodeId,
          typeLabels: props.typeLabels,
          onSelectNode: (nodeId: string) => emit('select-node', nodeId),
          onOpenResource: (resourceId: number) => emit('open-resource', resourceId),
          onToggleCollapse: (nodeId: string) => emit('toggle-collapse', nodeId),
        }))),
      ])
    }
  },
})
</script>

<style scoped>
.outline-node-row,
.outline-resource-row,
.outline-group-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 34px;
  border-radius: 7px;
  padding-right: 8px;
  font-size: 12px;
}

.outline-node-row {
  color: #1f3158;
  font-weight: 600;
}

.outline-node-row:hover,
.outline-node-row--selected {
  background: #eef3fb;
}

.outline-resource-row {
  color: #53627c;
  font-weight: 500;
}

.outline-resource-row:hover {
  background: #f7f9fc;
}

.outline-group-row {
  color: #8a95a8;
  font-size: 11px;
  font-weight: 700;
}

.outline-collapse {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  color: #64748b;
  font-size: 10px;
}

.outline-collapse:hover:not(:disabled) {
  background: white;
}

.outline-collapse--empty {
  opacity: 0;
}

.outline-resource-type {
  display: inline-flex;
  align-items: center;
  height: 18px;
  border-radius: 999px;
  background: #eaf0ff;
  padding: 0 6px;
  color: #4164b2;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}
</style>
```

- [ ] **Step 2: Wire outline imports into PlanDetailView**

In `Vue-frontend/src/views/PlanDetailView.vue`, add imports:

```ts
import KnowledgeTreeOutline from '@/components/tree/KnowledgeTreeOutline.vue'
import { buildTreePlanOutline } from '@/components/tree/useTreePlanOutline'
import { useKnowledgeTreeStore } from '@/stores/knowledgeTree'
```

Add store:

```ts
const knowledgeTreeStore = useKnowledgeTreeStore()
```

Add computed values near the existing `modules` computed:

```ts
const rootTreeNodeId = computed(() => {
  const root = knowledgeTreeStore.nodes.find(node => !node.parentId)
  return root?.id || knowledgeTreeStore.nodes[0]?.id || null
})

const treePlanOutline = computed(() => buildTreePlanOutline(
  knowledgeTreeStore.nodes,
  resources.value,
  rootTreeNodeId.value,
))
```

- [ ] **Step 3: Add outline handlers to PlanDetailView**

Add these methods near `selectModule()` / `toggleResource()`:

```ts
async function selectTreeNode(nodeId: string) {
  await knowledgeTreeStore.selectNode(nodeId)
}

async function toggleTreeNodeCollapse(nodeId: string) {
  await knowledgeTreeStore.toggleCollapsed(nodeId)
}

async function openOutlineResource(resourceId: number) {
  await exitTreeMode()
  await nextTick()
  await openResourceById(resourceId)
}
```

`exitTreeMode()` is introduced in Task 7. If Task 5 is implemented before Task 7, add a temporary local function and replace it in Task 7:

```ts
async function exitTreeMode() {
  await router.replace({ query: { ...route.query, view: undefined } })
}
```

- [ ] **Step 4: Render outline in tree mode**

In the left sidebar module-list area in `PlanDetailView.vue`, wrap the existing module list content:

```vue
<KnowledgeTreeOutline
  v-if="isTreeMode"
  :items="treePlanOutline"
  :selected-node-id="knowledgeTreeStore.currentNodeId"
  :type-labels="typeLabels"
  @select-node="selectTreeNode"
  @open-resource="openOutlineResource"
  @toggle-collapse="toggleTreeNodeCollapse"
/>
<div v-else class="flex-1 overflow-y-auto p-3 space-y-2">
  <!-- keep the existing module list markup here unchanged -->
</div>
```

`isTreeMode` is introduced in Task 7. If Task 5 is implemented before Task 7, add this temporary computed and replace it in Task 7:

```ts
const isTreeMode = computed(() => route.query.view === 'tree')
```

- [ ] **Step 5: Run Vue type-adjacent tests**

Run:

```bash
cd Vue-frontend
npm test -- src/components/tree/useTreePlanOutline.test.ts
```

Expected: tests still pass.

- [ ] **Step 6: Commit**

```bash
git add Vue-frontend/src/components/tree/KnowledgeTreeOutline.vue Vue-frontend/src/views/PlanDetailView.vue
git commit -m "feat: add tree plan outline sidebar"
```

---

## Task 6: Sylva-Style Canvas and Split Popover

**Files:**
- Modify: `Vue-frontend/src/components/tree/KnowledgeTreeNode.vue`
- Modify: `Vue-frontend/src/components/tree/KnowledgeTreeCanvas.vue`
- Create: `Vue-frontend/src/components/tree/TreeSubdividePopover.vue`

- [ ] **Step 1: Simplify node card actions to structural split only**

In `Vue-frontend/src/components/tree/KnowledgeTreeNode.vue`, change emits:

```ts
const emit = defineEmits<{
  select: [nodeId: string]
  'toggle-collapse': [nodeId: string]
  'open-subdivide': [nodeId: string]
}>()
```

Replace the current "解释/拆分/第一性原理" action block with:

```vue
<div class="mt-3 flex items-center justify-between gap-2 border-t border-navy-100/70 pt-2">
  <div class="min-w-0 text-[11px] text-navy-400">
    <span v-if="node.isFundamental">第一性原理</span>
    <span v-else>结构节点</span>
  </div>
  <button class="node-action node-action--primary" title="选择拆分方法" @click.stop="emit('open-subdivide', node.id)">
    <svg class="h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M8 6h13" /><path d="M8 12h13" /><path d="M8 18h13" /><path d="M3 6h.01" /><path d="M3 12h.01" /><path d="M3 18h.01" />
    </svg>
    <span class="truncate">拆分</span>
  </button>
</div>
```

Add CSS:

```css
.node-action--primary {
  background: rgb(234 240 255);
  color: rgb(65 100 178);
}

.node-action--primary:hover {
  background: rgb(214 225 255);
  color: rgb(31 49 88);
}
```

- [ ] **Step 2: Update canvas event contract and visual shell**

In `Vue-frontend/src/components/tree/KnowledgeTreeCanvas.vue`, change node usage:

```vue
<KnowledgeTreeNode
  v-for="item in layout.items"
  :key="item.node.id"
  class="absolute"
  :style="nodeStyle(item)"
  :node="item.node"
  :selected="item.node.id === selectedNodeId"
  :has-children="childrenByParent.has(item.node.id)"
  @select="$emit('select', $event)"
  @toggle-collapse="$emit('toggle-collapse', $event)"
  @open-subdivide="$emit('open-subdivide', $event)"
/>
```

Change emits:

```ts
const emit = defineEmits<{
  select: [nodeId: string]
  'toggle-collapse': [nodeId: string]
  'open-subdivide': [nodeId: string]
  'update:panX': [value: number]
  'update:panY': [value: number]
  'update:zoom': [value: number]
}>()
```

Change the root class to include a canvas grid:

```vue
class="knowledge-tree-canvas relative h-full w-full overflow-hidden rounded-lg border border-navy-100 bg-white"
```

Move the zoom toolbar from top-left to bottom-center by replacing the toolbar wrapper class:

```vue
<div class="absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 rounded-lg border border-navy-100 bg-white/95 px-2 py-1 shadow-paper">
```

Add scoped CSS:

```css
.knowledge-tree-canvas {
  background-image:
    linear-gradient(rgba(51, 65, 85, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(51, 65, 85, 0.05) 1px, transparent 1px);
  background-size: 28px 28px;
}
```

- [ ] **Step 3: Create TreeSubdividePopover component**

Create `Vue-frontend/src/components/tree/TreeSubdividePopover.vue`:

```vue
<template>
  <Teleport to="body">
    <div v-if="node" class="split-overlay" role="dialog" aria-modal="true" @click.self="$emit('close')">
      <section class="split-panel">
        <header class="split-head">
          <div class="min-w-0">
            <div class="split-eyebrow">想怎么拆开它</div>
            <h2 class="split-title">「{{ node.title }}」</h2>
          </div>
          <button class="split-close" title="关闭" @click="$emit('close')">x</button>
        </header>

        <div v-if="step === 'choice'" class="split-body">
          <button class="split-choice" @click="loadOptions">
            <span class="split-choice-title">按知识点拆分</span>
            <span class="split-choice-desc">AI 挑几个合适角度，拆成并列的子知识点</span>
          </button>
          <button class="split-choice" @click="startFirstPrinciples">
            <span class="split-choice-title">第一性原理 · 拆到底</span>
            <span class="split-choice-desc">一层层找出更底层的前置知识，长任务可停止</span>
          </button>
        </div>

        <div v-else-if="step === 'loading'" class="split-loading">
          <span class="split-dot"></span>
          <span>AI 正在挑选拆分角度...</span>
        </div>

        <div v-else class="split-body">
          <button v-if="options.length >= 2" class="split-multi" @click="$emit('multi-angle', options)">
            <span class="split-multi-title">按这 {{ options.length }} 个角度一次全拆</span>
            <span class="split-multi-desc">{{ options.map(option => option.label).join('、') }}</span>
          </button>

          <div v-if="options.length" class="split-divider"><span>或者只挑一个角度</span></div>

          <button
            v-for="option in options"
            :key="`${option.angle}:${option.label}`"
            class="split-option"
            @click="$emit('single-angle', option.angle)"
          >
            <span class="split-option-label">{{ option.label }}</span>
            <span class="split-option-rationale">{{ option.rationale }}</span>
          </button>

          <div class="split-custom">
            <input
              v-model="customAngle"
              maxlength="60"
              placeholder="或者自己写一个角度，比如「按场景拆」"
              @keydown.enter.prevent="submitCustom"
            />
            <button @click="submitCustom">按这个拆</button>
          </div>
        </div>

        <p v-if="error" class="split-error">{{ error }}</p>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { KnowledgeNode, TreeSubdivisionOption } from '@/types/knowledgeTree'

const props = defineProps<{
  node: KnowledgeNode | null
  options: TreeSubdivisionOption[]
  loading: boolean
  error?: string
}>()

const emit = defineEmits<{
  close: []
  'load-options': []
  'single-angle': [angle: string]
  'multi-angle': [options: TreeSubdivisionOption[]]
  'first-principles': []
}>()

const step = ref<'choice' | 'loading' | 'options'>('choice')
const customAngle = ref('')

watch(() => props.node?.id, () => {
  step.value = 'choice'
  customAngle.value = ''
})

watch(() => props.loading, loading => {
  if (loading) step.value = 'loading'
  else if (step.value === 'loading') step.value = 'options'
})

function loadOptions() {
  step.value = 'loading'
  emit('load-options')
}

function startFirstPrinciples() {
  emit('first-principles')
}

function submitCustom() {
  const angle = customAngle.value.trim()
  if (!angle) return
  emit('single-angle', angle)
}
</script>

<style scoped>
.split-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.22);
  padding: 24px;
}

.split-panel {
  width: min(520px, 100%);
  border: 1px solid rgba(26, 40, 71, 0.12);
  border-radius: 10px;
  background: white;
  box-shadow: 0 18px 48px rgba(26, 40, 71, 0.2);
}

.split-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(26, 40, 71, 0.08);
  padding: 16px;
}

.split-eyebrow {
  color: #7c8aa5;
  font-size: 12px;
  font-weight: 700;
}

.split-title {
  margin-top: 4px;
  overflow: hidden;
  color: #1f3158;
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.split-close {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  color: #7c8aa5;
}

.split-close:hover {
  background: #f2f5fa;
  color: #1f3158;
}

.split-body {
  display: grid;
  gap: 10px;
  padding: 16px;
}

.split-choice,
.split-option,
.split-multi {
  display: grid;
  gap: 5px;
  border: 1px solid rgba(26, 40, 71, 0.1);
  border-radius: 8px;
  padding: 12px;
  text-align: left;
}

.split-choice:hover,
.split-option:hover,
.split-multi:hover {
  border-color: rgba(65, 100, 178, 0.28);
  background: #f7f9ff;
}

.split-choice-title,
.split-multi-title,
.split-option-label {
  color: #1f3158;
  font-size: 13px;
  font-weight: 700;
}

.split-choice-desc,
.split-multi-desc,
.split-option-rationale {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.split-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 22px 16px;
  color: #53627c;
  font-size: 13px;
}

.split-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #4164b2;
  animation: splitPulse 1s ease-in-out infinite;
}

.split-divider {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #8a95a8;
  font-size: 11px;
}

.split-divider::before,
.split-divider::after {
  content: "";
  height: 1px;
  flex: 1;
  background: rgba(26, 40, 71, 0.08);
}

.split-custom {
  display: flex;
  gap: 8px;
}

.split-custom input {
  min-width: 0;
  flex: 1;
  border: 1px solid rgba(26, 40, 71, 0.12);
  border-radius: 8px;
  padding: 0 10px;
  color: #1f3158;
  font-size: 12px;
}

.split-custom button {
  height: 34px;
  border-radius: 8px;
  background: #eaf0ff;
  padding: 0 12px;
  color: #4164b2;
  font-size: 12px;
  font-weight: 700;
}

.split-error {
  border-top: 1px solid rgba(248, 113, 113, 0.18);
  padding: 10px 16px 14px;
  color: #dc2626;
  font-size: 12px;
}

@keyframes splitPulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}
</style>
```

- [ ] **Step 4: Run Vue tree tests**

Run:

```bash
cd Vue-frontend
npm test -- src/components/tree/useTreeLayout.test.ts src/components/tree/useTreePlanOutline.test.ts
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add Vue-frontend/src/components/tree/KnowledgeTreeNode.vue Vue-frontend/src/components/tree/KnowledgeTreeCanvas.vue Vue-frontend/src/components/tree/TreeSubdividePopover.vue
git commit -m "feat: add sylva style tree split UI"
```

---

## Task 7: Same-Page Tree Mode in Plan Detail

**Files:**
- Modify: `Vue-frontend/src/views/PlanDetailView.vue`
- Modify: `Vue-frontend/src/config/routeComponents.ts`

- [ ] **Step 1: Add PlanDetail imports**

In `Vue-frontend/src/views/PlanDetailView.vue`, add:

```ts
import KnowledgeTreeCanvas from '@/components/tree/KnowledgeTreeCanvas.vue'
import TreeSubdividePopover from '@/components/tree/TreeSubdividePopover.vue'
import type { TreeSubdivisionOption } from '@/types/knowledgeTree'
```

Task 5 already added:

```ts
import KnowledgeTreeOutline from '@/components/tree/KnowledgeTreeOutline.vue'
import { buildTreePlanOutline } from '@/components/tree/useTreePlanOutline'
import { useKnowledgeTreeStore } from '@/stores/knowledgeTree'
```

- [ ] **Step 2: Add mode state and route sync**

Near existing `planId` computed:

```ts
const isTreeMode = computed(() => route.query.view === 'tree')
const treePopoverNodeId = ref<string | null>(null)
const treeSubdivisionOptions = ref<TreeSubdivisionOption[]>([])
```

Add computed selected node:

```ts
const selectedTreeNode = computed(() =>
  knowledgeTreeStore.nodes.find(node => node.id === knowledgeTreeStore.currentNodeId) || null
)

const treePopoverNode = computed(() =>
  knowledgeTreeStore.nodes.find(node => node.id === treePopoverNodeId.value) || null
)
```

Add mode handlers:

```ts
async function enterTreeMode() {
  selectedResourceId.value = null
  selectedResource.value = null
  quizData.value = null
  mindmapData.value = null
  gradingResult.value = null
  quizSubmittedAnswers.value = null
  showExplanations.value = false
  isFullscreen.value = false
  await router.replace({ query: { ...route.query, view: 'tree' } })
  await ensureTreeLoaded()
}

async function exitTreeMode() {
  treePopoverNodeId.value = null
  await router.replace({ query: { ...route.query, view: undefined } })
}

async function ensureTreeLoaded() {
  if (!Number.isFinite(planId.value)) return
  if (knowledgeTreeStore.tree?.planId === planId.value && knowledgeTreeStore.nodes.length > 0) return
  await knowledgeTreeStore.loadByPlan(planId.value)
}
```

Add watcher:

```ts
watch(isTreeMode, async value => {
  if (value) {
    await ensureTreeLoaded()
  } else {
    treePopoverNodeId.value = null
  }
}, { immediate: true })
```

- [ ] **Step 3: Change knowledge tree header button**

Replace the existing button click:

```vue
@click="$router.push(`/plan/${planId}/tree`)"
```

with:

```vue
@click="enterTreeMode"
```

Add active state:

```vue
:class="isTreeMode ? 'text-navy-600 bg-navy-50' : 'text-navy-300 hover:text-navy-600 hover:bg-navy-50'"
```

- [ ] **Step 4: Render tree mode across the full right area**

Wrap the existing resource panel, divider, and `PlanChatPanel` in:

```vue
<template v-if="isTreeMode">
  <section class="flex min-w-[720px] flex-1 flex-col overflow-hidden rounded-lg border border-navy-100 bg-white shadow-paper">
    <header class="flex flex-shrink-0 items-center justify-between gap-3 border-b border-navy-100 px-4 py-3">
      <div class="min-w-0">
        <h3 class="truncate text-sm font-display font-semibold text-navy-800">
          {{ knowledgeTreeStore.tree?.title || plan.title }}
        </h3>
        <p class="mt-0.5 truncate text-xs text-navy-400">
          {{ selectedTreeNode?.title || '选择节点后开始拆分' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="knowledgeTreeStore.activeSource"
          class="h-8 rounded-lg bg-red-50 px-3 text-xs font-semibold text-red-600 hover:bg-red-100"
          @click="knowledgeTreeStore.stopStream"
        >
          停止
        </button>
        <button class="btn-secondary h-8 px-3 py-0 text-xs" :disabled="knowledgeTreeStore.loading" @click="ensureTreeLoaded">
          刷新
        </button>
        <button class="h-8 rounded-lg px-3 text-xs font-semibold text-navy-500 hover:bg-navy-50" @click="exitTreeMode">
          返回学习
        </button>
      </div>
    </header>

    <div v-if="knowledgeTreeStore.error" class="mx-4 mt-3 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
      {{ knowledgeTreeStore.error }}
    </div>

    <div class="relative min-h-0 flex-1 p-3">
      <KnowledgeTreeCanvas
        :nodes="knowledgeTreeStore.nodes"
        :root-node-id="rootTreeNodeId"
        :selected-node-id="knowledgeTreeStore.currentNodeId"
        v-model:pan-x="knowledgeTreeStore.panX"
        v-model:pan-y="knowledgeTreeStore.panY"
        v-model:zoom="knowledgeTreeStore.zoom"
        @select="selectTreeNode"
        @toggle-collapse="toggleTreeNodeCollapse"
        @open-subdivide="openTreeSubdivide"
      />
      <div v-if="knowledgeTreeStore.loading && !knowledgeTreeStore.activeSource" class="absolute inset-3 flex items-center justify-center rounded-lg bg-white/60">
        <svg class="h-8 w-8 animate-spin text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" class="opacity-25" />
          <path d="M4 12a8 8 0 0 1 8-8" class="opacity-75" stroke-linecap="round" />
        </svg>
      </div>
    </div>
  </section>

  <TreeSubdividePopover
    :node="treePopoverNode"
    :options="treeSubdivisionOptions"
    :loading="knowledgeTreeStore.subdivisionOptionsLoading"
    :error="knowledgeTreeStore.subdivisionOptionsError"
    @close="closeTreeSubdivide"
    @load-options="loadTreeSubdivideOptions"
    @single-angle="runSingleAngleSplit"
    @multi-angle="runMultiAngleSplit"
    @first-principles="runFirstPrinciplesSplit"
  />
</template>

<template v-else>
  <!-- existing resource panel, divider, and PlanChatPanel remain here unchanged -->
</template>
```

- [ ] **Step 5: Add split popover handlers**

Add methods:

```ts
async function openTreeSubdivide(nodeId: string) {
  const selected = await knowledgeTreeStore.selectNode(nodeId)
  if (!selected) return
  treeSubdivisionOptions.value = []
  treePopoverNodeId.value = nodeId
}

function closeTreeSubdivide() {
  treePopoverNodeId.value = null
  treeSubdivisionOptions.value = []
}

async function loadTreeSubdivideOptions() {
  treeSubdivisionOptions.value = await knowledgeTreeStore.loadSubdivisionOptionsCurrent()
}

async function runSingleAngleSplit(angle: string) {
  closeTreeSubdivide()
  await knowledgeTreeStore.subdivideCurrent(angle)
}

async function runMultiAngleSplit(options: TreeSubdivisionOption[]) {
  closeTreeSubdivide()
  await knowledgeTreeStore.multiAngleSubdivideCurrent(options)
}

async function runFirstPrinciplesSplit() {
  closeTreeSubdivide()
  await knowledgeTreeStore.firstPrinciplesCurrent()
}
```

- [ ] **Step 6: Make old tree route redirect into same page mode**

In `Vue-frontend/src/config/routeComponents.ts`, replace the current `PlanKnowledgeTree` route:

```ts
routes.push({
  path: 'plan/:planId/tree',
  name: 'PlanKnowledgeTree',
  component: componentMap['knowledge-tree'],
  props: true,
  meta: { fullWidth: true },
})
```

with:

```ts
routes.push({
  path: 'plan/:planId/tree',
  name: 'PlanKnowledgeTree',
  redirect: to => ({
    name: 'PlanDetail',
    params: { id: to.params.planId },
    query: { ...to.query, view: 'tree' },
  }),
  meta: { fullWidth: true },
})
```

- [ ] **Step 7: Run frontend tests**

Run:

```bash
cd Vue-frontend
npm test -- src/api/knowledgeTree.test.ts src/stores/knowledgeTree.test.ts src/components/tree/useTreeLayout.test.ts src/components/tree/useTreePlanOutline.test.ts
```

Expected: targeted frontend tests pass.

- [ ] **Step 8: Commit**

```bash
git add Vue-frontend/src/views/PlanDetailView.vue Vue-frontend/src/config/routeComponents.ts
git commit -m "feat: embed knowledge tree in plan detail"
```

---

## Task 8: Route Compatibility and UX Polish

**Files:**
- Modify: `Vue-frontend/src/views/KnowledgeTreeView.vue`
- Modify: `Vue-frontend/src/components/layout/AppSidebar.vue` only if needed

- [ ] **Step 1: Decide if `KnowledgeTreeView.vue` is still referenced**

Run:

```bash
cd Vue-frontend
rg -n "KnowledgeTreeView|knowledge-tree|PlanKnowledgeTree" src
```

Expected: `KnowledgeTreeView.vue` remains referenced only by `componentMap['knowledge-tree']` or menu routes. If admin/menu config still has a direct `knowledge-tree` page, keep the component as a safe redirect screen.

- [ ] **Step 2: Convert KnowledgeTreeView into compatibility redirect**

Replace `Vue-frontend/src/views/KnowledgeTreeView.vue` with:

```vue
<template>
  <div class="flex h-full items-center justify-center text-sm text-navy-400">
    正在打开知识树...
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const planId = route.params.planId || route.params.id
  if (planId) {
    router.replace({ name: 'PlanDetail', params: { id: planId }, query: { ...route.query, view: 'tree' } })
  } else {
    router.replace('/plan/create')
  }
})
</script>
```

- [ ] **Step 3: Verify sidebar active logic**

Run:

```bash
cd Vue-frontend
rg -n "PlanKnowledgeTree|knowledge-tree" src/components/layout/AppSidebar.vue src/stores/permission.ts
```

If `AppSidebar.vue` still checks `route.name === 'PlanKnowledgeTree'`, keep it. If the redirect means active state should key off `route.query.view === 'tree'`, change only the knowledge-tree branch to:

```ts
if (path === '/knowledge-tree') {
  return route.name === 'PlanKnowledgeTree'
    || route.path === path
    || (route.name === 'PlanDetail' && route.query.view === 'tree')
}
```

- [ ] **Step 4: Run frontend tests**

Run:

```bash
cd Vue-frontend
npm test -- src/api/knowledgeTree.test.ts src/stores/knowledgeTree.test.ts src/components/tree/useTreePlanOutline.test.ts
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add Vue-frontend/src/views/KnowledgeTreeView.vue Vue-frontend/src/components/layout/AppSidebar.vue
git commit -m "chore: redirect legacy knowledge tree route"
```

---

## Task 9: End-to-End Verification

**Files:**
- No code changes expected.

- [ ] **Step 1: Run Java tests**

Run:

```bash
cd Java-backend
mvn test
```

Expected: Java tests pass. If unrelated failures appear, record exact failing class and method in the final handoff.

- [ ] **Step 2: Run targeted Python tests**

Run:

```bash
cd Python-backend
python -m pytest tests/test_knowledge_tree_ai.py tests/test_knowledge_tree_endpoints.py -q
```

Expected: targeted Python tests pass.

- [ ] **Step 3: Run targeted Vue tests**

Run:

```bash
cd Vue-frontend
npm test -- src/api/knowledgeTree.test.ts src/stores/knowledgeTree.test.ts src/components/tree/useTreeLayout.test.ts src/components/tree/useTreePlanOutline.test.ts
```

Expected: targeted Vue tests pass.

- [ ] **Step 4: Try Vue full test suite**

Run:

```bash
cd Vue-frontend
npm test
```

Expected: tests pass. If existing unrelated failures appear, record them.

- [ ] **Step 5: Do not require Vue build as the main gate**

Current known unrelated build blockers exist in:

- `Vue-frontend/src/components/resource/QuizPlayer.vue`
- `Vue-frontend/src/stores/planCreate.ts`
- missing `gsap`
- `Vue-frontend/src/views/admin/TokenAnalysis.vue`
- `Vue-frontend/src/views/admin/UserManagement.vue`

Run build only as an informational check:

```bash
cd Vue-frontend
npm run build
```

Expected: build may fail on unrelated existing issues. Do not claim this feature broke build unless new knowledge-tree files appear in the error output.

- [ ] **Step 6: Manual browser verification**

Start the Vue dev server:

```bash
cd Vue-frontend
npm run dev
```

Open the local URL shown by Vite, then verify:

- `/plan/:id` opens in original learning/resource mode.
- Clicking the knowledge-tree icon switches to `?view=tree`.
- The left sidebar shows root node, child nodes, and lightweight resource rows.
- The right side no longer shows the chat panel or resource panel in tree mode.
- The right side shows a full tree canvas with pan/zoom.
- Clicking node `拆分` opens the split popover.
- "按知识点拆分" loads options.
- Single angle split creates child nodes.
- Multi-angle split creates angle grouping nodes and children.
- "第一性原理 · 拆到底" creates fundamental child nodes.
- Stop button closes an active stream and leaves already-created nodes visible.
- Clicking a resource row switches back to learning/resource mode and opens the resource.
- Visiting `/plan/:id/tree` redirects to `/plan/:id?view=tree`.

- [ ] **Step 7: Final status**

Prepare final response with:

- What changed.
- Tests run and outcomes.
- Any unrelated failures.
- Whether commits were created.

---

## Self-Review

- Spec coverage: The plan covers same-page mode switching, full right-area takeover, left tree outline, Sylva-style split popover, angle suggestions, multi-angle grouped split, custom single-angle split, first-principles split, stop action, resource mounting, route compatibility, and test gates.
- Placeholder scan: No `TBD`, `TODO`, "similar to", or unspecified edge handling remains. Each implementation step names exact files and code to add.
- Type consistency: `TreeSubdivisionOption`, `TreeSubdivisionOptionsResponse`, `streamTreeMultiAngleSubdivide`, `getTreeSubdivisionOptions`, `loadSubdivisionOptionsCurrent`, and `multiAngleSubdivideCurrent` are introduced before use by later tasks.
- Scope check: Drag-and-drop ordering and resource generation from tree mode are intentionally excluded. They are not required by the approved decisions.
