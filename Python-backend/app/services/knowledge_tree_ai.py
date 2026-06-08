import asyncio
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
            yield {"type": "quiz", "data": result.get("questions", [])}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("quiz_node failed")
            yield {"type": "error", "content": str(exc)}

    async def flashcards_node(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            search_results, context_chunks = await self._search("知识点闪卡")
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json([
                {"role": "system", "content": "严格输出 JSON：{\"flashcards\":[{\"question\":\"...\",\"answer\":\"...\",\"difficulty\":1}]}"},
                {"role": "user", "content": self._flashcards_prompt(node_id, context_chunks)},
            ])
            yield {"type": "flashcards", "data": result.get("flashcards", [])}
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
    def _first_principles_json_system_prompt() -> str:
        return (
            "你是第一性原理分析助手。严格输出 JSON："
            "{\"children\":[{\"title\":\"...\",\"summary\":\"...\",\"importance\":1,\"difficulty\":1,"
            "\"fpRelation\":\"supports\",\"fpReason\":\"...\"}]}"
        )


def get_knowledge_tree_ai_service() -> KnowledgeTreeAiService:
    return KnowledgeTreeAiService()
