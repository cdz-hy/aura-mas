import asyncio
import json
import logging
import queue
import threading
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Iterable, List, Optional

from app.agents.llm_factory import get_quiz_generator_llm, get_tutor_llm
from app.services.db.java_client import java_client as default_java_client
from app.services.retrieval import HybridRetrievalService

logger = logging.getLogger("knowledge_tree_ai")

MODE_LIMITS = {
    "Lite": (3, 4),
    "Medium": (5, 7),
    "Zen": (8, 12),
}


class KnowledgeTreeAiService:
    def __init__(self, java_client=None, retriever=None, llm=None, json_llm=None):
        self.java_client = java_client or default_java_client
        self.retriever = retriever if retriever is not None else HybridRetrievalService()
        self.llm = llm or get_tutor_llm()
        self.json_llm = json_llm or (llm if llm is not None and hasattr(llm, "chat_json") else None) or get_quiz_generator_llm()

    async def explain_node(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        message: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            search_results, context_chunks = await self._search(message)
            yield {"type": "search_results", "data": search_results}

            self.java_client.add_tree_message(node_id, {
                "role": "USER",
                "content": message,
                "searchSources": search_results,
            })

            prompt = self._explain_prompt(tree_id, node_id, message, context_chunks)
            assistant_text = ""
            async for chunk in self._stream_chunks([
                {"role": "system", "content": "你是 Aura 知识树学习助手，回答要清晰、循序渐进。"},
                {"role": "user", "content": prompt},
            ]):
                assistant_text += chunk
                yield {"type": "stream_text", "content": chunk}

            saved = self.java_client.add_tree_message(node_id, {
                "role": "ASSISTANT",
                "content": assistant_text,
                "searchSources": search_results,
            })
            yield {"type": "message_saved", "message": saved}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("explain_node failed")
            yield {"type": "error", "content": str(exc)}

    async def subdivide_node(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        angle: str = "",
        mode: str = "Lite",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            node_context = self._build_node_context(user_id, tree_id, node_id)
            query = " ".join(part for part in [
                node_context.get("node", {}).get("title"),
                angle or "拆分知识节点",
            ] if part)
            search_results, context_chunks = await self._search(query)
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": self._children_json_system_prompt()},
                {"role": "user", "content": self._subdivide_prompt(node_id, angle, context_chunks, node_context, mode)},
            ])
            children = self._limit_children(self._coerce_children(result), mode)
            nodes = self._create_grouped_children(tree_id, node_id, result, angle, children, node_context)
            yield {"type": "nodes_created", "nodes": nodes}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("subdivide_node failed")
            yield {"type": "error", "content": str(exc)}

    async def suggest_subdivision_options(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        mode: str = "Lite",
    ) -> Dict[str, Any]:
        node_context = self._build_node_context(user_id, tree_id, node_id)
        search_query = f"{node_context.get('node', {}).get('title', '')} 知识点拆分角度".strip()
        search_results, context_chunks = await self._search(search_query or "知识点拆分角度")
        result = await self._chat_json([
            {"role": "system", "content": self._subdivision_options_json_system_prompt()},
            {"role": "user", "content": self._subdivision_options_prompt(node_id, context_chunks, node_context, mode)},
        ])
        return {
            "tree_id": tree_id,
            "node_id": node_id,
            "options": self._normalize_subdivision_options(result),
            "caution": self._normalize_caution(result),
            "search_results": search_results,
        }

    async def multi_angle_subdivide(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        angles: List[Dict[str, str]],
        mode: str = "Lite",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            normalized_angles = self._normalize_requested_angles(angles)
            if not normalized_angles:
                yield {"type": "error", "content": "请选择至少一个拆分角度"}
                return

            node_context = self._build_node_context(user_id, tree_id, node_id)
            search_results, context_chunks = await self._search(" ".join(a["label"] for a in normalized_angles))
            yield {"type": "search_results", "data": search_results}

            result = await self._chat_json([
                {"role": "system", "content": self._multi_angle_json_system_prompt()},
                {"role": "user", "content": self._multi_angle_prompt(node_id, normalized_angles, context_chunks, node_context, mode)},
            ])
            groups = self._normalize_angle_groups(result, normalized_angles, self._child_limit_for_mode(mode))
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

    async def first_principles(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        mode: str = "Lite",
        max_depth: int = 3,
        is_disconnected: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            node_context = self._build_node_context(user_id, tree_id, node_id)
            search_query = f"{node_context.get('node', {}).get('title', '')} 第一性原理 基础概念".strip()
            search_results, context_chunks = await self._search(search_query or "第一性原理 基础概念")
            yield {"type": "search_results", "data": search_results}
            frontier: List[tuple[Dict[str, Any], int, str]] = [
                (node_context.get("node", {"id": node_id, "title": node_id}), 0, node_context.get("path", node_id))
            ]
            total_created = 0
            while frontier:
                parent, rel_depth, path = frontier.pop(0)
                if rel_depth >= max_depth:
                    continue
                if is_disconnected is not None and await is_disconnected():
                    break

                result = await self._chat_json([
                    {"role": "system", "content": self._first_principles_json_system_prompt()},
                    {
                        "role": "user",
                        "content": self._first_principles_prompt(
                            str(parent.get("id") or node_id),
                            context_chunks,
                            node_context,
                            mode,
                            parent,
                            path,
                            rel_depth,
                            max_depth,
                        ),
                    },
                ])
                raw_principles = result.get("children", result.get("principles", [])) if isinstance(result, dict) else []
                principles = self._limit_children([item for item in raw_principles if isinstance(item, dict)], mode)
                if not principles:
                    continue

                nodes = []
                for idx, child in enumerate(principles):
                    payload = self._child_payload(tree_id, str(parent.get("id") or node_id), child, idx)
                    payload["isFundamental"] = bool(child.get("isFundamental", child.get("is_fundamental", False)))
                    payload["fpRelation"] = child.get("fpRelation") or child.get("relation") or child.get("fp_relation") or "supports"
                    payload["fpReason"] = child.get("fpReason") or child.get("reason") or child.get("why") or child.get("fp_reason") or child.get("summary", "")
                    created = self.java_client.create_tree_node(payload)
                    nodes.append(created)
                    if not payload["isFundamental"]:
                        child_path = f"{path} > {created.get('title', payload['title'])}"
                        frontier.append((created, rel_depth + 1, child_path))
                total_created += len(nodes)
                yield {"type": "nodes_created", "nodes": nodes}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("first_principles failed")
            yield {"type": "error", "content": str(exc)}

    async def quiz_node(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        plan_id: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            search_results, context_chunks = await self._search("知识点测验")
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": "严格输出 JSON：{\"questions\":[{\"question\":\"...\",\"options\":[\"A\"],\"answer\":\"A\",\"explanation\":\"...\"}]}"},
                {"role": "user", "content": self._quiz_prompt(node_id, plan_id, context_chunks)},
            ])
            questions = self._normalize_quiz_questions(result.get("questions", []) if isinstance(result, dict) else [])
            resource = self.java_client.create_resource(
                plan_id=plan_id,
                module_type="quiz",
                module_data={
                    "title": "节点练习题",
                    "description": f"知识树节点 {node_id} 自动生成练习题",
                    "questions": questions,
                    "totalPoints": sum(question.get("points", 1) for question in questions),
                    "estimatedMinutes": max(1, len(questions) * 2),
                },
                module_order=self._next_module_order(plan_id),
                generated_by_agent="knowledge_tree_quiz",
            )
            yield {
                "type": "resource_generated",
                "resources": [{
                    "id": resource.get("id"),
                    "type": "quiz",
                    "title": "节点练习题",
                }],
            }
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("quiz_node failed")
            yield {"type": "error", "content": str(exc)}

    async def flashcards_node(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        plan_id: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            search_results, context_chunks = await self._search("知识点闪卡")
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": "严格输出 JSON：{\"flashcards\":[{\"question\":\"...\",\"answer\":\"...\",\"difficulty\":1}]}"},
                {"role": "user", "content": self._flashcards_prompt(node_id, context_chunks)},
            ])
            raw_cards = self._extract_flashcards(result)
            cards = self._normalize_flashcards(raw_cards)
            if not cards:
                yield {"type": "error", "content": "未能生成闪卡，请重试"}
                return

            note_id = self._find_note_id_for_node(plan_id, node_id)
            if note_id is None:
                self.java_client.create_resource(
                    plan_id=plan_id,
                    module_type="text",
                    module_data={
                        "title": "知识树闪卡来源",
                        "content": self._flashcard_source_text(node_id, context_chunks, cards),
                        "nodeId": node_id,
                        "flashcards": cards,
                    },
                    module_order=self._next_module_order(plan_id),
                    generated_by_agent="knowledge_tree_flashcards",
                )
            else:
                self.java_client._request("POST", "/api/flashcard/internal/save", json={
                    "userId": user_id,
                    "noteId": note_id,
                    "cards": cards,
                })
            yield {"type": "flashcards_generated", "cards": cards}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("flashcards_node failed")
            yield {"type": "error", "content": str(exc)}

    async def _search(self, query: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not self.retriever or not hasattr(self.retriever, "search"):
            return [], []
        try:
            result = await self.retriever.search(query, limit=12, rerank_top_n=5)
            if not isinstance(result, dict):
                return [], []
            return result.get("final_results", []) or [], result.get("context_chunks", []) or []
        except Exception as exc:
            logger.warning("knowledge tree retrieval failed: %s", exc)
            return [], []

    async def _stream_chunks(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        chunks: queue.Queue = queue.Queue()
        sentinel = object()

        def run() -> None:
            try:
                for chunk in self.llm.chat_stream(messages):
                    if chunk:
                        chunks.put(str(chunk))
                chunks.put(sentinel)
            except Exception as exc:
                chunks.put(exc)

        threading.Thread(target=run, daemon=True).start()

        while True:
            item = await asyncio.to_thread(chunks.get)
            if item is sentinel:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    async def _chat_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return await asyncio.to_thread(self.json_llm.chat_json, messages)

    def _build_node_context(self, user_id: int, tree_id: str, node_id: str) -> Dict[str, Any]:
        try:
            tree_response = self.java_client.get_tree(tree_id, user_id)
        except Exception as exc:
            logger.warning("knowledge tree context fetch failed: %s", exc)
            tree_response = {}

        tree = tree_response.get("tree", {}) if isinstance(tree_response, dict) else {}
        nodes = tree_response.get("nodes", []) if isinstance(tree_response, dict) else []
        nodes = [node for node in nodes if isinstance(node, dict)]
        by_id = {str(node.get("id")): node for node in nodes if node.get("id") is not None}
        node = by_id.get(node_id) or {"id": node_id, "title": node_id}
        parent_id = node.get("parentId") or node.get("parent_id")
        parent = by_id.get(str(parent_id)) if parent_id else None
        siblings = [
            item for item in nodes
            if (item.get("parentId") or item.get("parent_id")) == parent_id and str(item.get("id")) != node_id
        ]
        children = [
            item for item in nodes
            if (item.get("parentId") or item.get("parent_id")) == node_id
        ]
        path_nodes = []
        cursor = node
        seen = set()
        while cursor and cursor.get("id") not in seen:
            seen.add(cursor.get("id"))
            path_nodes.append(cursor)
            cursor_parent_id = cursor.get("parentId") or cursor.get("parent_id")
            cursor = by_id.get(str(cursor_parent_id)) if cursor_parent_id else None
        path = " > ".join(reversed([str(item.get("title") or item.get("id") or "") for item in path_nodes if item]))

        try:
            messages = self.java_client.get_tree_messages(node_id)
        except Exception:
            messages = []

        return {
            "tree": tree,
            "node": node,
            "parent": parent,
            "path": path or str(node.get("title") or node_id),
            "siblings": siblings,
            "children": children,
            "messages": [msg for msg in messages[-4:] if isinstance(msg, dict)] if isinstance(messages, list) else [],
        }

    def _create_child_nodes(self, tree_id: str, node_id: str, children: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        nodes = []
        for idx, child in enumerate(children):
            nodes.append(self.java_client.create_tree_node(self._child_payload(tree_id, node_id, child, idx)))
        return nodes

    def _create_grouped_children(
        self,
        tree_id: str,
        node_id: str,
        result: Any,
        angle: str,
        children: Iterable[Dict[str, Any]],
        node_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        children = list(children)
        current_title = str(node_context.get("node", {}).get("title") or "").strip()
        group_title = self._group_title(result, angle, current_title)
        group_summary = ""
        if isinstance(result, dict):
            group_summary = str(result.get("rationale") or result.get("summary") or "").strip()
        group_node = self.java_client.create_tree_node({
            "treeId": tree_id,
            "parentId": node_id,
            "title": group_title,
            "summary": group_summary or f"按{angle or '学习顺序'}组织 {current_title or '当前节点'} 的下一层知识点。",
            "content": "",
            "status": "pending",
            "importance": 2,
            "relevanceScore": 2,
            "difficulty": 2,
            "sortOrder": len(node_context.get("children", [])),
            "collapsed": False,
        })
        group_id = str(group_node.get("id"))
        nodes = [group_node]
        for idx, child in enumerate(children):
            nodes.append(self.java_client.create_tree_node(self._child_payload(tree_id, group_id, child, idx)))
        return nodes

    @staticmethod
    def _child_payload(tree_id: str, node_id: str, child: Dict[str, Any], idx: int) -> Dict[str, Any]:
        return {
            "treeId": tree_id,
            "parentId": node_id,
            "title": child.get("title", f"子节点 {idx + 1}"),
            "summary": child.get("summary", ""),
            "content": child.get("content", child.get("summary", "")),
            "status": child.get("status", "pending"),
            "importance": child.get("importance", 1),
            "difficulty": child.get("difficulty", 1),
            "depth": child.get("depth"),
            "sortOrder": child.get("sortOrder", idx),
            "prerequisiteIds": child.get("prerequisiteIds", []),
            "collapsed": child.get("collapsed", False),
        }

    @staticmethod
    def _coerce_children(result: Any) -> List[Dict[str, Any]]:
        if isinstance(result, dict):
            children = result.get("children", [])
        elif isinstance(result, list):
            children = result
        else:
            children = []
        return [child for child in children if isinstance(child, dict)]

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        text = str(mode or "Lite").strip()
        return text if text in MODE_LIMITS else "Lite"

    @classmethod
    def _child_limit_for_mode(cls, mode: str) -> int:
        return MODE_LIMITS[cls._normalize_mode(mode)][1]

    @classmethod
    def _target_range_for_mode(cls, mode: str) -> str:
        low, high = MODE_LIMITS[cls._normalize_mode(mode)]
        return f"{low}-{high}"

    @classmethod
    def _limit_children(cls, children: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        return children[:cls._child_limit_for_mode(mode)]

    @staticmethod
    def _group_title(result: Any, angle: str, current_title: str) -> str:
        if isinstance(result, dict):
            for key in ("middle_title", "middleTitle", "group_title", "groupTitle", "label", "title"):
                value = str(result.get(key) or "").strip()
                if value:
                    return value[:50]
        clean_angle = (angle or "学习顺序").strip()
        if current_title:
            return f"{clean_angle}拆{current_title}"[:50]
        return f"{clean_angle}拆分"[:50]

    @staticmethod
    def _normalize_requested_angles(angles: List[Dict[str, str]]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for item in angles[:4]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("angle") or "").strip()
            angle = str(item.get("angle") or label).strip()
            rationale = str(item.get("rationale") or "").strip()
            if not label or not angle:
                continue
            normalized.append({
                "angle": angle[:60],
                "label": label[:40],
                "rationale": rationale[:180],
            })
        return normalized

    @staticmethod
    def _normalize_subdivision_options(result: Any) -> List[Dict[str, str]]:
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

    @staticmethod
    def _normalize_caution(result: Any) -> Optional[Dict[str, str]]:
        if not isinstance(result, dict):
            return None
        raw = result.get("caution")
        if not isinstance(raw, dict):
            return None
        label = str(raw.get("label") or raw.get("title") or "先别拆").strip()
        rationale = str(raw.get("rationale") or raw.get("reason") or raw.get("summary") or "").strip()
        if not rationale:
            return None
        return {
            "label": label[:40] or "先别拆",
            "rationale": rationale[:220],
        }

    def _normalize_angle_groups(
        self,
        result: Any,
        requested_angles: List[Dict[str, str]],
        child_limit: int = 5,
    ) -> List[Dict[str, Any]]:
        raw_groups = result.get("groups", []) if isinstance(result, dict) else []
        groups_by_angle = {}
        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            key = str(group.get("angle") or group.get("label") or "").strip()
            children = self._coerce_children({"children": group.get("children", [])})[:child_limit]
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

    @staticmethod
    def _normalize_quiz_questions(raw_questions: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_questions, list):
            return []
        questions = []
        for idx, item in enumerate(raw_questions):
            if not isinstance(item, dict):
                continue
            question = item.get("question") or item.get("question_text") or item.get("prompt") or ""
            correct_answer = (
                item.get("correctAnswer")
                or item.get("correct_answer")
                or item.get("answer")
                or item.get("correct")
                or ""
            )
            questions.append({
                "index": item.get("index", idx),
                "type": item.get("type") or item.get("question_type") or "single_choice",
                "question": question,
                "options": item.get("options") or [],
                "correctAnswer": correct_answer,
                "explanation": item.get("explanation") or item.get("analysis") or "",
                "difficulty": KnowledgeTreeAiService._coerce_int(item.get("difficulty"), 3),
                "points": KnowledgeTreeAiService._coerce_int(item.get("points"), 1),
            })
        return questions

    @staticmethod
    def _extract_flashcards(result: Any) -> Any:
        if isinstance(result, dict):
            return result.get("flashcards") or result.get("cards") or []
        if isinstance(result, list):
            return result
        return []

    @staticmethod
    def _normalize_flashcards(raw_cards: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_cards, list):
            return []
        cards = []
        for item in raw_cards:
            if not isinstance(item, dict):
                continue
            question = item.get("question") or item.get("question_text") or item.get("front") or item.get("q") or ""
            answer = item.get("answer") or item.get("answer_text") or item.get("back") or item.get("a") or ""
            if not str(question).strip() or not str(answer).strip():
                continue
            cards.append({
                "question": str(question).strip(),
                "answer": str(answer).strip(),
                "difficulty": KnowledgeTreeAiService._coerce_int(
                    item.get("difficulty", item.get("level", item.get("difficulty_level", 1))),
                    1,
                ),
            })
        return cards

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _next_module_order(self, plan_id: int) -> int:
        try:
            resources = self.java_client.get_plan_resources(plan_id)
        except Exception:
            return 1
        orders = []
        for resource in resources or []:
            if not isinstance(resource, dict):
                continue
            order = resource.get("moduleOrder")
            if order is None:
                order = resource.get("module_order")
            try:
                orders.append(int(order))
            except (TypeError, ValueError):
                continue
        return max(orders, default=0) + 1

    def _find_note_id_for_node(self, plan_id: int, node_id: str) -> Optional[int]:
        try:
            resources = self.java_client.get_plan_resources(plan_id)
        except Exception:
            return None
        for resource in resources or []:
            if not isinstance(resource, dict):
                continue
            module_data = self._parse_module_data(resource.get("moduleData"))
            resource_node_id = (
                resource.get("nodeId")
                or module_data.get("nodeId")
                or module_data.get("node_id")
            )
            if resource_node_id != node_id:
                continue
            note_id = (
                resource.get("noteId")
                or resource.get("note_id")
                or module_data.get("noteId")
                or module_data.get("note_id")
            )
            if note_id is not None:
                try:
                    return int(note_id)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _parse_module_data(module_data: Any) -> Dict[str, Any]:
        if isinstance(module_data, dict):
            return module_data
        if isinstance(module_data, str):
            try:
                parsed = json.loads(module_data)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _flashcard_source_text(self, node_id: str, context_chunks: List[Dict[str, Any]], cards: List[Dict[str, Any]]) -> str:
        card_lines = "\n".join(f"- Q: {card['question']}\n  A: {card['answer']}" for card in cards)
        return (
            f"知识树节点：{node_id}\n\n"
            f"参考资料：\n{self._context_text(context_chunks)}\n\n"
            f"生成闪卡：\n{card_lines}"
        )

    @staticmethod
    def _context_text(context_chunks: List[Dict[str, Any]]) -> str:
        if not context_chunks:
            return "无检索上下文。"
        parts = []
        for idx, chunk in enumerate(context_chunks[:5], 1):
            title = chunk.get("doc_title") or chunk.get("title") or "资料"
            content = chunk.get("content") or chunk.get("parent_content") or ""
            parts.append(f"[{idx}] {title}\n{content[:1200]}")
        return "\n\n".join(parts)

    def _node_context_text(self, node_context: Dict[str, Any]) -> str:
        tree = node_context.get("tree", {}) or {}
        node = node_context.get("node", {}) or {}
        parts = [
            f"计划目标：{tree.get('title') or '未命名计划'}",
        ]
        if tree.get("contextSummary"):
            parts.append(f"计划摘要：{tree.get('contextSummary')}")
        parts.extend([
            f"当前节点：{node.get('title') or node.get('id')}",
            f"节点摘要：{node.get('summary') or '无'}",
            f"节点内容：{node.get('content') or '无'}",
            f"节点路径：{node_context.get('path') or node.get('title') or node.get('id')}",
            f"兄弟节点：{self._node_list_text(node_context.get('siblings', []))}",
            f"已有子节点：{self._node_list_text(node_context.get('children', []))}",
            f"最近对话：{self._message_list_text(node_context.get('messages', []))}",
        ])
        return "\n".join(parts)

    @staticmethod
    def _node_list_text(nodes: List[Dict[str, Any]]) -> str:
        if not nodes:
            return "无"
        return "；".join(
            f"{item.get('title') or item.get('id')}{'（' + str(item.get('summary'))[:80] + '）' if item.get('summary') else ''}"
            for item in nodes[:6]
        )

    @staticmethod
    def _message_list_text(messages: List[Dict[str, Any]]) -> str:
        if not messages:
            return "无"
        lines = []
        for message in messages:
            role = message.get("role") or "UNKNOWN"
            content = str(message.get("content") or "").replace("\n", " ")[:160]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _explain_prompt(self, tree_id: str, node_id: str, message: str, context_chunks: List[Dict[str, Any]]) -> str:
        return f"tree_id={tree_id}, node_id={node_id}\n用户问题：{message}\n\n可参考资料：\n{self._context_text(context_chunks)}"

    def _subdivide_prompt(
        self,
        node_id: str,
        angle: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
    ) -> str:
        return (
            f"请拆分节点 {node_id}。拆分角度：{angle or '按学习顺序'}。"
            f"模式：{self._normalize_mode(mode)}，目标数量：{self._target_range_for_mode(mode)} 个具体子节点。"
            "无论角度是否单一，都先产出 middle_title 作为中间分组节点标题，再产出 children。"
            "\n\n节点上下文：\n"
            f"{self._node_context_text(node_context)}"
            f"\n\n资料：\n{self._context_text(context_chunks)}"
        )

    def _first_principles_prompt(
        self,
        node_id: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
        parent: Optional[Dict[str, Any]] = None,
        path: str = "",
        rel_depth: int = 0,
        max_depth: int = 3,
    ) -> str:
        parent = parent or node_context.get("node", {})
        return (
            f"请为节点 {node_id} 提炼更底层的第一性原理子节点。"
            "每个子节点必须说明 fpRelation/fpReason，并标注 isFundamental。"
            f"当前层级：{rel_depth}/{max_depth}。模式：{self._normalize_mode(mode)}，每层目标数量：{self._target_range_for_mode(mode)} 个。"
            f"\n当前拆解对象：{parent.get('title') or parent.get('id')}"
            f"\n对象摘要：{parent.get('summary') or '无'}"
            f"\n节点路径：{path or node_context.get('path')}"
            "\n\n起点上下文：\n"
            f"{self._node_context_text(node_context)}"
            f"\n\n资料：\n{self._context_text(context_chunks)}"
        )

    def _subdivision_options_prompt(
        self,
        node_id: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
    ) -> str:
        return (
            f"请为知识树节点 node_id={node_id} 推荐 3 个适合继续拆分的角度。"
            "角度必须能生成并列的学习子节点，避免泛泛而谈。"
            f"模式：{self._normalize_mode(mode)}，目标数量：{self._target_range_for_mode(mode)} 个具体子节点。"
            "同时给出 caution，说明什么情况下不建议继续拆。"
            "\n\n节点上下文：\n"
            f"{self._node_context_text(node_context)}"
            f"\n参考资料：\n{self._context_text(context_chunks)}"
        )

    def _multi_angle_prompt(
        self,
        node_id: str,
        angles: List[Dict[str, str]],
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
    ) -> str:
        return (
            f"请把知识树节点 node_id={node_id} 按这些角度一次性拆开："
            f"{json.dumps(angles, ensure_ascii=False)}。"
            "每个角度先形成一个分组节点，再在分组下生成具体可学习子节点。"
            f"模式：{self._normalize_mode(mode)}，每组目标数量：{self._target_range_for_mode(mode)} 个具体子节点。"
            "\n\n节点上下文：\n"
            f"{self._node_context_text(node_context)}"
            f"\n参考资料：\n{self._context_text(context_chunks)}"
        )

    def _quiz_prompt(self, node_id: str, plan_id: int, context_chunks: List[Dict[str, Any]]) -> str:
        return f"请为 plan_id={plan_id}, node_id={node_id} 生成 3 道测验题。\n资料：\n{self._context_text(context_chunks)}"

    def _flashcards_prompt(self, node_id: str, context_chunks: List[Dict[str, Any]]) -> str:
        return f"请为 node_id={node_id} 生成 5 张闪卡。\n资料：\n{self._context_text(context_chunks)}"

    @staticmethod
    def _children_json_system_prompt() -> str:
        return (
            "你是知识树拆分助手。严格输出 JSON："
            "{\"middle_title\":\"按某角度拆某节点\","
            "\"children\":[{\"title\":\"...\",\"summary\":\"...\",\"importance\":1,\"difficulty\":1}]}"
        )

    @staticmethod
    def _subdivision_options_json_system_prompt() -> str:
        return (
            "严格输出 JSON："
            "{\"options\":[{\"angle\":\"stable_key\",\"label\":\"按概念拆\","
            "\"rationale\":\"为什么这个角度适合当前节点\"}],"
            "\"caution\":{\"label\":\"先别拆\",\"rationale\":\"为什么当前可能不适合继续拆\"}}。"
            "只返回 2 到 4 个拆分角度。"
        )

    @staticmethod
    def _multi_angle_json_system_prompt() -> str:
        return (
            "严格输出 JSON：{\"groups\":[{\"angle\":\"by_concept\",\"label\":\"按概念拆\","
            "\"rationale\":\"拆分理由\",\"children\":[{\"title\":\"子知识点\",\"summary\":\"说明\","
            "\"importance\":3,\"difficulty\":2}]}]}。"
            "每个 group 对应用户给定的一个角度，每组 children 生成 2 到 5 个。"
        )

    @staticmethod
    def _first_principles_json_system_prompt() -> str:
        return (
            "你是第一性原理分析助手。严格输出 JSON："
            "{\"children\":[{\"title\":\"...\",\"summary\":\"...\",\"importance\":1,\"difficulty\":1,"
            "\"isFundamental\":false,\"fpRelation\":\"supports\",\"fpReason\":\"...\"}]}"
        )


def get_knowledge_tree_ai_service() -> KnowledgeTreeAiService:
    return KnowledgeTreeAiService()
