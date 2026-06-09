import asyncio
import json
import logging
import queue
import threading
from typing import Any, AsyncGenerator, Dict, Iterable, List, Optional

from app.agents.llm_factory import get_quiz_generator_llm, get_tutor_llm
from app.services.db.java_client import java_client as default_java_client
from app.services.retrieval import HybridRetrievalService

logger = logging.getLogger("knowledge_tree_ai")


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
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            query = angle or "拆分知识节点"
            search_results, context_chunks = await self._search(query)
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": self._children_json_system_prompt()},
                {"role": "user", "content": self._subdivide_prompt(node_id, angle, context_chunks)},
            ])
            children = self._coerce_children(result)
            nodes = self._create_child_nodes(tree_id, node_id, children)
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

    async def first_principles(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            search_results, context_chunks = await self._search("第一性原理 基础概念")
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": self._first_principles_json_system_prompt()},
                {"role": "user", "content": self._first_principles_prompt(node_id, context_chunks)},
            ])
            principles = result.get("children", result.get("principles", [])) if isinstance(result, dict) else []
            nodes = []
            for idx, child in enumerate(principles):
                payload = self._child_payload(tree_id, node_id, child, idx)
                payload["isFundamental"] = True
                payload["fpRelation"] = child.get("fpRelation") or child.get("relation") or "supports"
                payload["fpReason"] = child.get("fpReason") or child.get("reason") or child.get("summary", "")
                nodes.append(self.java_client.create_tree_node(payload))
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

    def _create_child_nodes(self, tree_id: str, node_id: str, children: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        nodes = []
        for idx, child in enumerate(children):
            nodes.append(self.java_client.create_tree_node(self._child_payload(tree_id, node_id, child, idx)))
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

    def _explain_prompt(self, tree_id: str, node_id: str, message: str, context_chunks: List[Dict[str, Any]]) -> str:
        return f"tree_id={tree_id}, node_id={node_id}\n用户问题：{message}\n\n可参考资料：\n{self._context_text(context_chunks)}"

    def _subdivide_prompt(self, node_id: str, angle: str, context_chunks: List[Dict[str, Any]]) -> str:
        return f"请拆分节点 {node_id}。拆分角度：{angle or '按学习顺序'}。\n资料：\n{self._context_text(context_chunks)}"

    def _first_principles_prompt(self, node_id: str, context_chunks: List[Dict[str, Any]]) -> str:
        return f"请为节点 {node_id} 提炼第一性原理子节点。\n资料：\n{self._context_text(context_chunks)}"

    def _subdivision_options_prompt(self, node_id: str, context_chunks: List[Dict[str, Any]]) -> str:
        return (
            f"请为知识树节点 node_id={node_id} 推荐 3 个适合继续拆分的角度。"
            "角度必须能生成并列的学习子节点，避免泛泛而谈。"
            f"\n参考资料：\n{self._context_text(context_chunks)}"
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

    def _quiz_prompt(self, node_id: str, plan_id: int, context_chunks: List[Dict[str, Any]]) -> str:
        return f"请为 plan_id={plan_id}, node_id={node_id} 生成 3 道测验题。\n资料：\n{self._context_text(context_chunks)}"

    def _flashcards_prompt(self, node_id: str, context_chunks: List[Dict[str, Any]]) -> str:
        return f"请为 node_id={node_id} 生成 5 张闪卡。\n资料：\n{self._context_text(context_chunks)}"

    @staticmethod
    def _children_json_system_prompt() -> str:
        return (
            "你是知识树拆分助手。严格输出 JSON："
            "{\"children\":[{\"title\":\"...\",\"summary\":\"...\",\"importance\":1,\"difficulty\":1}]}"
        )

    @staticmethod
    def _subdivision_options_json_system_prompt() -> str:
        return (
            "严格输出 JSON："
            "{\"options\":[{\"angle\":\"stable_key\",\"label\":\"按概念拆\","
            "\"rationale\":\"为什么这个角度适合当前节点\"}]}。"
            "只返回 2 到 4 个拆分角度，不要返回 caution/先别拆。"
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
            "\"fpRelation\":\"supports\",\"fpReason\":\"...\"}]}"
        )


def get_knowledge_tree_ai_service() -> KnowledgeTreeAiService:
    return KnowledgeTreeAiService()
