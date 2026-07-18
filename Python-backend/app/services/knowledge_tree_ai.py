import asyncio
import difflib
import json
import logging
import math
import queue
import re
import threading
import time
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from app.agents.llm_factory import get_tree_lightweight_json_llm, get_tutor_llm
from app.services.db.java_client import java_client as default_java_client
from app.services.retrieval import HybridRetrievalService

logger = logging.getLogger("knowledge_tree_ai")

MODE_LIMITS = {
    "Lite": (2, 3),
    "Medium": (3, 4),
    "Zen": (4, 5),
}

# 知识树最大深度（0=根，1=主模块，2=细分知识点，3=最细知识点）
MAX_TREE_DEPTH = 3
# 多角度拆分时每组最多子节点（Lite 再收紧）
MAX_MULTI_ANGLE_GROUPS = {"Lite": 2, "Medium": 3, "Zen": 3}

# 模糊去重阈值：SequenceMatcher 相似度 >= 此值视为重复
FUZZY_DEDUP_RATIO = 0.85
# 语义搜索粗筛上限：节点数超过它就先本地打分截断，避免 prompt 随树膨胀
RANK_PREFILTER_MAX = 40
# 前缀缓存：这些键在同一节点/模式下逐轮基本不变，抽到前置 system 消息里
_CACHEABLE_PROMPT_KEYS = (
    "task",
    "instructions",
    "json_schema",
    "field",
    "current_problem",
    "learning_background",
)
# 节点上下文内存缓存 TTL（秒）
CONTEXT_CACHE_TTL = 30
# 拆分选项缓存 TTL（秒）
OPTIONS_CACHE_TTL = 300
# embedding 语义去重阈值（余弦相似度）
SEMANTIC_DEDUP_THRESHOLD = 0.88

# 模块级 options 缓存: key -> (expires_at, payload)
_options_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def clamp_metric(value: Any) -> int:
    """将 importance/relevance_score/difficulty 钳制到 1-3 范围。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 2
    return max(1, min(3, number))


def _looks_similar_topic(title: str, taken: set[str]) -> bool:
    """简单的相似度查重：防止 AI 生成"消费决策"和"消费者决策"这种近义重复。

    精确匹配或子串包含即视为重复，避免把高度近似的节点都放进树里。
    """
    if not title:
        return True
    norm = title.replace(" ", "").lower()
    if norm in taken:
        return True
    for existing in taken:
        e_norm = existing.replace(" ", "").lower()
        if norm == e_norm:
            return True
        if len(norm) >= 4 and len(e_norm) >= 4 and (norm in e_norm or e_norm in norm):
            return True
    return False


def _looks_similar(candidate: str, existing: Iterable[str]) -> bool:
    """跨全树的近似 title 去重：精确相等或 ratio > FUZZY_DEDUP_RATIO 视为重复。"""
    cand = candidate.strip()
    if not cand:
        return True
    for raw in existing:
        other = (raw or "").strip()
        if not other:
            continue
        if cand == other:
            return True
        if difflib.SequenceMatcher(None, cand, other).ratio() >= FUZZY_DEDUP_RATIO:
            return True
    return False


def calibrate_relevance_distribution(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """相关度分布校准：避免所有子节点都被标成"高度相关"。

    高相关（relevance_score=3）的节点数不能超过总数的一半（至少保留 1 个），
    多余的降级为 2。这保证树中"真正核心"的节点有区分度。
    """
    if len(items) < 3:
        return items
    high_indexes = [i for i, item in enumerate(items) if clamp_metric(item.get("relevance_score", 2)) >= 3]
    max_high = max(1, (len(items) + 1) // 2)
    for index in high_indexes[max_high:]:
        items[index]["relevance_score"] = 2
        items[index]["relevance"] = 0
    for item in items:
        score = clamp_metric(item.get("relevance_score", 2))
        item["relevance_score"] = score
        item["relevance"] = 1 if score >= 3 else 0
    return items


def _prefilter_nodes_by_query(
    candidates: List[Dict[str, Any]], query: str, limit: int
) -> List[Dict[str, Any]]:
    """零 LLM 成本的本地粗筛：按 query 与 title/summary 的子串命中 + 模糊比相似度打分，取 top-N。

    只在节点数超过 RANK_PREFILTER_MAX 时调用；目的是把交给 LLM 精排的候选集封顶，
    让搜索的 prompt 体积不随知识树增长而膨胀。粗筛宁可多放进（召回优先），精排交给 LLM。
    """
    q = query.lower()
    q_terms = [t for t in re.split(r"\s+", q) if t]

    def score(node: Dict[str, Any]) -> float:
        title = (node.get("title") or "").lower()
        summary = (node.get("summary") or "").lower()
        hay = f"{title} {summary}"
        s = 0.0
        if q in title:
            s += 5.0
        elif q in summary:
            s += 3.0
        for term in q_terms:
            if term and term in hay:
                s += 1.5
        s += difflib.SequenceMatcher(None, q, title).ratio()
        return s

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[:limit]


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """计算两个向量的余弦相似度。"""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _cached_chat_messages(system_rule: str, prompt: Dict[str, Any]) -> List[Dict[str, str]]:
    """构造命中前缀缓存的消息序列。

    顺序 = [固定输出规则] + [固定 task/instructions/json_schema] + [每轮会变的数据]。
    前两条 system 消息在同节点同模式的连续追问里逐字相同，LLM 会按前缀命中缓存，
    只有末尾 user 消息（用户问题、最近对话、节点状态）每轮变化。
    """
    volatile = {k: v for k, v in prompt.items() if k not in _CACHEABLE_PROMPT_KEYS}
    static = {k: prompt[k] for k in _CACHEABLE_PROMPT_KEYS if k in prompt}
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_rule}]
    if static:
        messages.append(
            {
                "role": "system",
                "content": (
                    "本次任务的固定规则与输出格式(请严格遵守约定的 json_schema):\n"
                    + json.dumps(static, ensure_ascii=False)
                ),
            }
        )
    messages.append({"role": "user", "content": json.dumps(volatile, ensure_ascii=False)})
    return messages


class KnowledgeTreeAiService:
    # 第一性原理拆解：同一 BFS 层内并发展开的并发上限，兼顾加速与对 LLM/Java 后端的压力。
    FIRST_PRINCIPLES_CONCURRENCY = 3

    def __init__(self, java_client=None, retriever=None, llm=None, json_llm=None, light_llm=None):
        self.java_client = java_client or default_java_client
        self.retriever = retriever if retriever is not None else HybridRetrievalService()
        self.llm = llm or get_tutor_llm()
        # 结构化 JSON 统一走 light_llm（关闭思维链）；测试可注入 json_llm/light_llm
        self.structured_llm = (
            light_llm
            or json_llm
            or (llm if llm is not None and hasattr(llm, "chat_json") else None)
            or get_tree_lightweight_json_llm()
        )
        self.light_llm = self.structured_llm
        self.json_llm = self.structured_llm
        self._context_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._title_embedding_cache: Dict[str, List[float]] = {}
        self._embedder = None

    async def explain_node(
        self,
        user_id: int,
        tree_id: str,
        node_id: str,
        message: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            node_context = self._build_node_context(user_id, tree_id, node_id)
            search_query = " ".join(part for part in [
                node_context.get("node", {}).get("title"),
                message,
            ] if part)
            search_results, context_chunks = await self._search(search_query or message)
            yield {"type": "search_results", "data": search_results}

            self.java_client.add_tree_message(node_id, {
                "role": "USER",
                "content": message,
                "searchSources": search_results,
            })

            yield {"type": "thinking", "content": "正在结合节点上下文组织回答…"}
            prompt_text = self._explain_prompt(tree_id, node_id, message, context_chunks, node_context)
            assistant_text = ""
            async for chunk in self._stream_chunks([
                {"role": "system", "content": "你是 Aura 知识树学习助手，回答要清晰、循序渐进。"},
                {"role": "user", "content": prompt_text},
            ]):
                assistant_text += chunk
                yield {"type": "stream_text", "content": chunk}

            saved = self.java_client.add_tree_message(node_id, {
                "role": "ASSISTANT",
                "content": assistant_text,
                "searchSources": search_results,
            })
            yield {"type": "message_saved", "message": saved}
            self._record_token_usage(user_id, "knowledge_tree_explain")
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
            depth_err = self._subdivide_depth_error(node_context)
            if depth_err:
                yield {"type": "error", "content": depth_err}
                return
            query = " ".join(part for part in [
                node_context.get("node", {}).get("title"),
                angle or "拆分知识节点",
            ] if part)
            yield {"type": "thinking", "content": "正在检索相关资料…"}
            search_results, context_chunks = await self._search(query)
            yield {"type": "search_results", "data": search_results}
            yield {"type": "thinking", "content": "正在拆分知识点…"}
            prompt = self._subdivide_prompt_dict(node_id, angle, context_chunks, node_context, mode)
            result = await self._chat_json(_cached_chat_messages(
                self._children_json_system_prompt(),
                prompt,
            ))
            preview_title = self._split_preview_title(
                angle, str(node_context.get("node", {}).get("title") or ""),
            )
            yield {"type": "group_preview", "content": preview_title}
            children = self._limit_children(self._coerce_children(result), mode)
            children = self._dedup_and_calibrate(children, node_context)
            nodes = self._create_grouped_children(tree_id, node_id, result, angle, children, node_context)
            yield {"type": "nodes_created", "nodes": nodes}
            self._invalidate_context_cache(tree_id)
            self._record_token_usage(user_id, "knowledge_tree_subdivide")
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
        cache_key = f"{tree_id}:{node_id}:{self._normalize_mode(mode)}"
        cached = _options_cache.get(cache_key)
        if cached and cached[0] > time.time():
            return cached[1]

        node_context = self._build_node_context(user_id, tree_id, node_id)
        depth_err = self._subdivide_depth_error(node_context)
        if depth_err:
            return {
                "tree_id": tree_id,
                "node_id": node_id,
                "options": [],
                "caution": {
                    "label": "已达最深层",
                    "rationale": depth_err,
                },
                "search_results": [],
            }
        search_query = f"{node_context.get('node', {}).get('title', '')} 知识点拆分角度".strip()
        search_results, context_chunks = await self._search(search_query or "知识点拆分角度")
        prompt = self._subdivision_options_prompt_dict(node_id, context_chunks, node_context, mode)
        result = await self._chat_json(_cached_chat_messages(
            self._subdivision_options_json_system_prompt(),
            prompt,
        ))
        payload = {
            "tree_id": tree_id,
            "node_id": node_id,
            "options": self._normalize_subdivision_options(result),
            "caution": self._normalize_caution(result),
            "search_results": search_results,
        }
        # 本地 depth-based caution 兜底：LLM 可能漏给 caution
        if not payload.get("caution"):
            node = node_context.get("node", {}) or {}
            depth = int(node.get("depth") or 0)
            local_caution = self._depth_caution(depth, node.get("title", ""))
            if local_caution:
                payload["caution"] = local_caution
        _options_cache[cache_key] = (time.time() + OPTIONS_CACHE_TTL, payload)
        return payload

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
            depth_err = self._subdivide_depth_error(node_context)
            if depth_err:
                yield {"type": "error", "content": depth_err}
                return
            max_groups = MAX_MULTI_ANGLE_GROUPS.get(self._normalize_mode(mode), 2)
            normalized_angles = normalized_angles[:max_groups]
            yield {"type": "thinking", "content": "正在检索多角度拆分资料…"}
            search_results, context_chunks = await self._search(" ".join(a["label"] for a in normalized_angles))
            yield {"type": "search_results", "data": search_results}
            yield {"type": "thinking", "content": "正在按选定角度拆分…"}

            result = await self._chat_json(_cached_chat_messages(
                self._multi_angle_json_system_prompt(),
                self._multi_angle_prompt_dict(node_id, normalized_angles, context_chunks, node_context, mode),
            ))
            groups = self._normalize_angle_groups(result, normalized_angles, self._child_limit_for_mode(mode))
            # 跨 group 去重 + 校准：保证不同角度下不出现近似重复的子节点
            groups = self._dedup_angle_groups(groups, node_context)
            nodes: List[Dict[str, Any]] = []
            # 收集所有已存在的 title 用于跨 group 去重
            existing_titles = self._collect_existing_titles(node_context)
            taken_titles: set[str] = set(existing_titles)
            for group_index, group in enumerate(groups):
                group_title = self._dedup_title(group["label"], taken_titles)
                taken_titles.add(group_title)
                yield {"type": "group_preview", "content": group_title}
                parent_depth = int(node_context.get("node", {}).get("depth") or 0)
                attach_parent_id = node_id
                child_depth = parent_depth + 1
                if child_depth > MAX_TREE_DEPTH:
                    continue

                # 批量创建 children + 两遍法 prerequisite 映射
                child_payloads: List[Dict[str, Any]] = []
                child_prereqs: List[List[str]] = []
                for child_index, child in enumerate(group["children"]):
                    child_title = str(child.get("title") or "").strip()[:50]
                    if not child_title or self._looks_similar_enhanced(child_title, taken_titles):
                        continue
                    payload = self._child_payload(tree_id, attach_parent_id, child, child_index)
                    payload["depth"] = child_depth
                    child_payloads.append(payload)
                    taken_titles.add(child_title)
                    raw_prereqs = child.get("prerequisite_titles") or child.get("prerequisites") or []
                    prereq_titles = (
                        [str(p).strip()[:50] for p in raw_prereqs if str(p).strip()]
                        if isinstance(raw_prereqs, list)
                        else []
                    )
                    child_prereqs.append(prereq_titles)

                if child_payloads:
                    created_children = self.java_client.create_tree_nodes_batch(child_payloads)
                    nodes.extend(created_children)

                    # 解析依赖：只认本支兄弟 title，指向自己/不存在的丢弃
                    title_to_id: Dict[str, str] = {}
                    for created_node in created_children:
                        child_title = str(created_node.get("title") or "")
                        title_to_id[child_title] = str(created_node.get("id"))

                    for created_node, prereq_titles in zip(created_children, child_prereqs):
                        if not prereq_titles:
                            continue
                        resolved = [
                            title_to_id[t]
                            for t in prereq_titles
                            if t in title_to_id and title_to_id[t] != str(created_node.get("id"))
                        ]
                        resolved = list(dict.fromkeys(resolved))
                        if resolved:
                            self.java_client.update_tree_node(
                                str(created_node.get("id")),
                                {"prerequisiteIds": resolved},
                            )

                    yield {"type": "nodes_created", "nodes": nodes}
            self._record_token_usage(user_id, "knowledge_tree_multi_angle")
            self._invalidate_context_cache(tree_id)
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
        max_depth: int = 1,
        is_disconnected: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "start", "node_id": node_id}
        try:
            node_context = self._build_node_context(user_id, tree_id, node_id)
            depth_err = self._subdivide_depth_error(node_context)
            if depth_err:
                yield {"type": "error", "content": depth_err}
                return
            parent_depth = int(node_context.get("node", {}).get("depth") or 0)
            # DFS stack: (节点, 相对深度, 路径)
            safe_max_depth = max(1, min(int(max_depth), MAX_TREE_DEPTH - parent_depth))
            search_query = f"{node_context.get('node', {}).get('title', '')} 第一性原理 基础概念".strip()
            yield {"type": "thinking", "content": "正在检索基础概念资料…"}
            search_results, context_chunks = await self._search(search_query or "第一性原理 基础概念")
            yield {"type": "search_results", "data": search_results}

            stack: list[tuple[Dict[str, Any], int, str]] = [
                (node_context.get("node", {"id": node_id, "title": node_id}), 0, node_context.get("path", node_id))
            ]
            total_created = 0
            # 跨树去重 title 集合，防止第一性原理拆解时兜圈子
            taken_titles: set[str] = set(self._collect_existing_titles(node_context))

            while stack:
                # 客户端断连则停止，yield cancelled 事件
                if is_disconnected is not None and await is_disconnected():
                    yield {"type": "cancelled", "reason": "client_disconnected"}
                    return

                node, rel_depth, path = stack.pop()

                # 已超过安全深度，跳过此节点
                if rel_depth >= safe_max_depth:
                    continue

                # 对单个节点调一次 LLM，获取拆解出的基础原则
                yield {"type": "thinking", "content": f"正在拆解第 {rel_depth + 1} 层基础依赖…"}
                try:
                    result = await self._chat_json(_cached_chat_messages(
                        self._first_principles_json_system_prompt(),
                        self._first_principles_prompt_dict(
                            str(node.get("id") or node_id),
                            context_chunks,
                            node_context,
                            mode,
                            node,
                            path,
                            rel_depth,
                            safe_max_depth,
                        ),
                    ))
                except Exception as e:
                    logger.warning("first_principles LLM call failed: %s", e)
                    continue

                raw_principles = result.get("children", result.get("principles", [])) if isinstance(result, dict) else []
                is_fundamental = bool(result.get("is_fundamental")) if isinstance(result, dict) else False
                principles = self._limit_children([item for item in raw_principles if isinstance(item, dict)], mode)[:3]
                principles = self._dedup_principles(principles, taken_titles)
                current_node_id = str(node.get("id") or node_id)

                # 触底：当前节点已是基础公理/最小单位
                if is_fundamental or not principles:
                    if is_fundamental:
                        try:
                            updated = await asyncio.to_thread(
                                self.java_client.update_tree_node,
                                current_node_id,
                                {"isFundamental": True},
                            )
                            if isinstance(updated, dict):
                                node = {**node, **updated}
                        except Exception as e:
                            logger.warning("mark isFundamental failed: %s", e)
                    yield {
                        "type": "fp_layer",
                        "parent_id": current_node_id,
                        "parent_title": node.get("title", ""),
                        "children": [],
                        "reached_bottom": True,
                        "parent": node if is_fundamental else None,
                    }
                    continue

                # 逐个创建子节点（异步提交避免阻塞事件循环）
                created_nodes: List[Dict[str, Any]] = []
                node_depth = node.get("depth") or node_context.get("node", {}).get("depth") or 0
                non_fundamental_children: list[tuple[Dict[str, Any], str]] = []

                for idx, child in enumerate(principles):
                    child_depth = int(node_depth) + 1
                    if child_depth > MAX_TREE_DEPTH:
                        continue
                    payload = self._child_payload(tree_id, str(node.get("id") or node_id), child, idx)
                    payload["isFundamental"] = bool(child.get("isFundamental", child.get("is_fundamental", False)))
                    payload["fpRelation"] = child.get("fpRelation") or child.get("relation") or child.get("fp_relation") or "supports"
                    payload["fpReason"] = child.get("fpReason") or child.get("reason") or child.get("why") or child.get("fp_reason") or child.get("summary", "")
                    payload["depth"] = child_depth

                    try:
                        created = await asyncio.to_thread(self.java_client.create_tree_node, payload)
                    except Exception as e:
                        logger.warning("first_principles create_tree_node failed: %s", e)
                        continue

                    created_nodes.append(created)
                    child_title = str(created.get("title") or payload["title"])
                    taken_titles.add(child_title)

                    # 非触底节点收集起来，稍后按倒序压栈
                    if not payload["isFundamental"]:
                        child_path = f"{path} > {child_title}"
                        if int(created.get("depth") or payload["depth"]) < MAX_TREE_DEPTH:
                            non_fundamental_children.append((created, child_path))

                reached_bottom = len(non_fundamental_children) == 0

                if created_nodes:
                    total_created += len(created_nodes)
                    yield {
                        "type": "fp_layer",
                        "parent_id": str(node.get("id", node_id)),
                        "parent_title": node.get("title", ""),
                        "children": created_nodes,
                        "reached_bottom": reached_bottom,
                    }

                # 按倒序压栈，保证第一个子节点最先被展开（DFS 先左后右）
                for child, child_path in reversed(non_fundamental_children):
                    stack.append((child, rel_depth + 1, child_path))

            self._record_token_usage(user_id, "knowledge_tree_first_principles")
            self._invalidate_context_cache(tree_id)
            yield {"type": "done", "total_created": total_created}
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
            node_context = self._build_node_context(user_id, tree_id, node_id)
            node = node_context.get("node", {}) or {}
            search_query = " ".join(part for part in [
                node.get("title"),
                node.get("summary"),
                "测验题",
            ] if part)
            yield {"type": "thinking", "content": "正在检索节点相关资料…"}
            search_results, context_chunks = await self._search(search_query or "知识点测验")
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json_light([
                {"role": "system", "content": "严格输出 JSON：{\"questions\":[{\"question\":\"...\",\"options\":[\"A\"],\"answer\":\"A\",\"explanation\":\"...\"}]}"},
                {"role": "user", "content": self._quiz_prompt(node_id, plan_id, context_chunks, node_context)},
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
            self._record_token_usage(user_id, "knowledge_tree_quiz")
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
            node_context = self._build_node_context(user_id, tree_id, node_id)
            node = node_context.get("node", {}) or {}
            search_query = " ".join(part for part in [
                node.get("title"),
                node.get("summary"),
                "闪卡",
            ] if part)
            yield {"type": "thinking", "content": "正在检索节点相关资料…"}
            search_results, context_chunks = await self._search(search_query or "知识点闪卡")
            yield {"type": "search_results", "data": search_results}
            result = await self._chat_json_light([
                {"role": "system", "content": "严格输出 JSON：{\"flashcards\":[{\"question\":\"...\",\"answer\":\"...\",\"difficulty\":1}]}"},
                {"role": "user", "content": self._flashcards_prompt(node_id, context_chunks, node_context)},
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
            self._record_token_usage(user_id, "knowledge_tree_flashcards")
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("flashcards_node failed")
            yield {"type": "error", "content": str(exc)}

    async def bootstrap_tree(
        self,
        user_id: int,
        plan_id: int,
        tree_id: str,
        mode: str = "Lite",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """为初始树的一级模块批量生成子节点骨架。"""
        yield {"type": "start", "tree_id": tree_id}
        try:
            tree_response = self.java_client.get_tree(tree_id, user_id)
            nodes = tree_response.get("nodes", []) if isinstance(tree_response, dict) else []
            tree = tree_response.get("tree", {}) if isinstance(tree_response, dict) else {}
            root = next((n for n in nodes if not (n.get("parentId") or n.get("parent_id"))), None)
            if not root:
                yield {"type": "done"}
                return

            root_id = str(root.get("id"))
            l1_nodes = [
                n for n in nodes
                if (n.get("parentId") or n.get("parent_id")) == root_id
            ]
            # 仅对尚无子节点的一级模块做 bootstrap
            targets = []
            for l1 in l1_nodes:
                l1_id = str(l1.get("id"))
                has_child = any((n.get("parentId") or n.get("parent_id")) == l1_id for n in nodes)
                if not has_child:
                    targets.append(l1)
            if not targets:
                yield {"type": "done"}
                return

            yield {"type": "thinking", "content": f"正在为 {len(targets)} 个模块生成知识骨架…"}
            query = " ".join(part for part in [tree.get("title"), tree.get("contextSummary")] if part)
            search_results, context_chunks = await self._search(query or "学习路径")
            yield {"type": "search_results", "data": search_results}

            module_specs = [
                {"id": str(n.get("id")), "title": n.get("title"), "summary": n.get("summary") or ""}
                for n in targets
            ]
            prompt = {
                "task": "knowledge_tree_bootstrap",
                "instructions": (
                    "为每个一级模块生成细分知识点（children），每个模块 2-3 个。"
                    "不要一次生成最细知识点，只生成一层。"
                    "分类/总结类模块 → 细分知识点为子分类项；具体概念类 → 细分知识点。"
                    "不得扩展到物理/化学/材料学等无关基础学科。"
                    "children 不得与已有树节点 title 重复或近似。"
                ),
                "json_schema": {"modules": [{"module_id": "string", "children": []}]},
                "field": str(tree.get("field") or ""),
                "current_problem": str(tree.get("currentProblem") or ""),
                "learning_background": str(tree.get("learningBackground") or ""),
                "modules": module_specs,
                "existing_titles": [str(n.get("title")) for n in nodes if n.get("title")],
                "materials": self._context_text(context_chunks),
            }
            result = await self._chat_json(_cached_chat_messages(
                self._children_json_system_prompt(),
                prompt,
            ))
            raw_modules = result.get("modules", []) if isinstance(result, dict) else []
            targets_by_id = {str(n.get("id")): n for n in targets}
            all_created: List[Dict[str, Any]] = []
            for spec in raw_modules:
                if not isinstance(spec, dict):
                    continue
                node_id = str(spec.get("module_id") or "")
                l1 = targets_by_id.get(node_id)
                if not l1:
                    continue
                node_context = self._build_node_context(user_id, tree_id, node_id)
                children = self._limit_children(self._coerce_children(spec), mode)
                children = self._dedup_and_calibrate(children, node_context)
                if not children:
                    continue
                yield {"type": "thinking", "content": f"正在为「{l1.get('title')}」生成子节点…"}
                created = self._create_grouped_children(
                    tree_id, node_id, spec, "按学习顺序", children, node_context,
                )
                all_created.extend(created)
                if created:
                    yield {"type": "nodes_created", "nodes": created}

            self._invalidate_context_cache(tree_id)
            self._record_token_usage(user_id, "knowledge_tree_bootstrap")
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("bootstrap_tree failed")
            yield {"type": "error", "content": str(exc)}

    # ── 预览-确认流程 ──────────────────────────────────────────────

    async def preview_topics(
        self,
        user_id: int,
        plan_id: int,
        tree_id: str,
        mode: str = "Lite",
    ) -> List[Dict[str, str]]:
        """轻量预览：只生成 L1 主干标题列表，不展开 children。"""
        tree_response = self.java_client.get_tree(tree_id, user_id)
        tree = tree_response.get("tree", {}) if isinstance(tree_response, dict) else {}
        field = str(tree.get("field") or tree.get("title") or "新的学习主题")
        current_problem = str(tree.get("currentProblem") or "我想快速建立结构化认知")
        learning_background = str(tree.get("learningBackground") or "")

        mode_profile = {"Lite": (6, 8), "Medium": (8, 11), "Zen": (10, 14)}
        lo, hi = mode_profile.get(self._normalize_mode(mode), (6, 8))

        prompt = {
            "task": "preview_topics",
            "instructions": (
                f"请为「{field}」列出 {lo}-{hi} 个一级主干知识卡片。"
                f"用户当前问题：{current_problem}。"
                f"学习背景：{learning_background or '未说明'}。"
                "每个卡片只要 title(≤24字) + summary(≤60字)。"
                "顺序按建议学习先后排列。"
            ),
            "json_schema": {"topics": [{"title": "string", "summary": "string"}]},
        }
        result = await self._chat_json(
            _cached_chat_messages("你只输出合法 JSON，不输出 Markdown。", prompt)
        )
        raw_topics = result.get("topics", []) if isinstance(result, dict) else []
        cleaned: List[Dict[str, str]] = []
        taken: set[str] = set()
        for item in raw_topics:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()[:40]
            if not title or title in taken:
                continue
            taken.add(title)
            cleaned.append({
                "title": title,
                "summary": str(item.get("summary") or "").strip()[:160],
                "custom": False,
            })
        self._record_token_usage(user_id, "preview_topics")
        return cleaned

    async def grow_children_stream(
        self,
        user_id: int,
        tree_id: str,
        mode: str = "Lite",
        topics_override: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """用户确认主干后，逐个 branch SSE 流式生成 children。"""
        yield {"type": "start", "tree_id": tree_id}
        try:
            tree_response = self.java_client.get_tree(tree_id, user_id)
            nodes = tree_response.get("nodes", []) if isinstance(tree_response, dict) else []
            root = next(
                (n for n in nodes if not (n.get("parentId") or n.get("parent_id"))),
                None,
            )
            if not root:
                yield {"type": "all_done"}
                return

            root_id = str(root.get("id"))
            l1_nodes = [
                n for n in nodes if (n.get("parentId") or n.get("parent_id")) == root_id
            ]
            # 如果传了 topics_override，用它们更新 L1 节点的标题
            if topics_override and l1_nodes:
                override_map = {t["title"]: t for t in topics_override if isinstance(t, dict)}
                # TODO: 可在此处调用 java_client 更新 L1 节点标题（暂不实现，由前端处理）

            # 只为尚无 children 的 L1 节点生成
            targets: List[Dict[str, Any]] = []
            for l1 in l1_nodes:
                l1_id = str(l1.get("id"))
                has_child = any(
                    (n.get("parentId") or n.get("parent_id")) == l1_id for n in nodes
                )
                if not has_child:
                    targets.append(l1)
            if not targets:
                yield {"type": "all_done"}
                return

            yield {
                "type": "thinking",
                "content": f"正在为 {len(targets)} 个主干生成子知识点…",
            }

            # 并发跑所有 LLM 调用，FIFO emit 保证顺序
            tasks = [
                asyncio.create_task(self._expand_one_branch(user_id, tree_id, t, mode))
                for t in targets
            ]
            for target, task in zip(targets, tasks):
                try:
                    created = await task
                except Exception as e:
                    logger.warning("grow_children branch failed: %s", e)
                    created = []
                yield {
                    "type": "branch_done",
                    "parent_id": str(target.get("id")),
                    "parent_title": target.get("title", ""),
                    "children": created,
                }
                if created:
                    yield {"type": "nodes_created", "nodes": created}

            self._invalidate_context_cache(tree_id)
            self._record_token_usage(user_id, "grow_children")
            yield {"type": "all_done"}
        except Exception as exc:
            logger.exception("grow_children_stream failed")
            yield {"type": "error", "content": str(exc)}

    async def _expand_one_branch(
        self,
        user_id: int,
        tree_id: str,
        l1_node: Dict[str, Any],
        mode: str,
    ) -> List[Dict[str, Any]]:
        """为单个 L1 节点生成 children（供 grow_children_stream 并发调用）。"""
        node_id = str(l1_node.get("id"))
        node_context = self._build_node_context(user_id, tree_id, node_id)
        query = f"{l1_node.get('title', '')} 知识点拆分"
        _search_results, context_chunks = await self._search(query)
        prompt = self._subdivide_prompt_dict(node_id, "", context_chunks, node_context, mode)
        result = await self._chat_json(
            _cached_chat_messages(self._children_json_system_prompt(), prompt)
        )
        children = self._limit_children(self._coerce_children(result), mode)
        children = self._dedup_and_calibrate(children, node_context)
        if not children:
            return []
        return self._create_grouped_children(
            tree_id, node_id, result, "", children, node_context,
        )

    def sync_task_breakdown(
        self,
        user_id: int,
        plan_id: int,
        breakdown: Dict[str, Any],
        learning_background: str = "",
    ) -> Dict[str, Any]:
        """将 task_decomposer 产出的模块结构同步到知识树。"""
        try:
            return self.java_client.sync_task_breakdown(
                plan_id=plan_id,
                user_id=user_id,
                breakdown=breakdown,
                learning_background=learning_background,
            )
        except Exception as exc:
            logger.warning("sync_task_breakdown failed: %s", exc)
            return {"ok": False, "error": str(exc)}

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
        return await asyncio.to_thread(self.structured_llm.chat_json, messages)

    async def _chat_json_light(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """轻量结构化生成：使用 structured_llm。"""
        return await asyncio.to_thread(self.structured_llm.chat_json, messages)

    def _record_token_usage(self, user_id: int, scene: str) -> None:
        """把本次请求累积的 LLM token 用量上报到 Java 计费表，按模型分别记录。

        每个生成方法在 yield done 前调用一次。记录失败不应影响主流程，因此吞掉异常。
        """
        try:
            for client in (self.structured_llm,):
                if client is None or not hasattr(client, "get_usage_records"):
                    continue
                for record in client.get_usage_records():
                    self.java_client.record_token_usage(
                        user_id=user_id,
                        scene=scene,
                        model_name=record.get("model", ""),
                        input_tokens=int(record.get("input_tokens", 0)),
                        output_tokens=int(record.get("output_tokens", 0)),
                    )
        except Exception as exc:
            logger.warning("record token usage failed: %s", exc)

    def _build_node_context(self, user_id: int, tree_id: str, node_id: str) -> Dict[str, Any]:
        cache_key = f"{user_id}:{tree_id}:{node_id}"
        cached = self._context_cache.get(cache_key)
        if cached and cached[0] > time.time():
            return cached[1]

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

        context = {
            "tree": tree,
            "node": node,
            "parent": parent,
            "path": path or str(node.get("title") or node_id),
            "siblings": siblings,
            "children": children,
            "all_nodes": nodes,
            "messages": [msg for msg in messages[-4:] if isinstance(msg, dict)] if isinstance(messages, list) else [],
        }
        self._context_cache[cache_key] = (time.time() + CONTEXT_CACHE_TTL, context)
        return context

    def _invalidate_context_cache(self, tree_id: str) -> None:
        """节点变更后清除该树的上下文缓存。"""
        prefix = f":{tree_id}:"
        stale = [key for key in self._context_cache if prefix in key]
        for key in stale:
            self._context_cache.pop(key, None)

    def _get_embedder(self):
        if self._embedder is False:
            return None
        if self._embedder is None:
            try:
                from app.services.embedding import BailianEmbeddingService
                self._embedder = BailianEmbeddingService()
            except Exception as exc:
                logger.warning("embedding service unavailable for semantic dedup: %s", exc)
                self._embedder = False
        return self._embedder if self._embedder is not False else None

    def _embed_title(self, title: str) -> Optional[List[float]]:
        title = (title or "").strip()
        if not title:
            return None
        if title in self._title_embedding_cache:
            return self._title_embedding_cache[title]
        embedder = self._get_embedder()
        if not embedder:
            return None
        try:
            vector = embedder.embed_query(title)
            self._title_embedding_cache[title] = vector
            return vector
        except Exception as exc:
            logger.warning("embed title failed: %s", exc)
            return None

    def _looks_similar_enhanced(self, candidate: str, existing: Iterable[str]) -> bool:
        """字符串模糊去重 + embedding 语义去重。"""
        if _looks_similar(candidate, existing):
            return True
        cand_vec = self._embed_title(candidate)
        if not cand_vec:
            return False
        for raw in existing:
            other = (raw or "").strip()
            if not other:
                continue
            other_vec = self._embed_title(other)
            if other_vec and _cosine_similarity(cand_vec, other_vec) >= SEMANTIC_DEDUP_THRESHOLD:
                return True
        return False

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
        """每次拆分只插入一层 children，直接挂在当前节点下。"""
        children = list(children)
        parent_depth = int(node_context.get("node", {}).get("depth") or 0)
        if parent_depth >= MAX_TREE_DEPTH:
            return []

        nodes: List[Dict[str, Any]] = []
        child_payloads: List[Dict[str, Any]] = []
        child_prereqs: List[List[str]] = []
        for idx, child in enumerate(children):
            payload = self._child_payload(tree_id, node_id, child, idx)
            payload["depth"] = parent_depth + 1
            if payload["depth"] > MAX_TREE_DEPTH:
                continue
            child_payloads.append(payload)
            raw_prereqs = child.get("prerequisite_titles") or child.get("prerequisites") or []
            prereq_titles = (
                [str(p).strip()[:50] for p in raw_prereqs if str(p).strip()]
                if isinstance(raw_prereqs, list)
                else []
            )
            child_prereqs.append(prereq_titles)
        if not child_payloads:
            return nodes
        created_children = self.java_client.create_tree_nodes_batch(child_payloads)
        nodes.extend(created_children)
        title_to_id = {str(n.get("title") or ""): str(n.get("id")) for n in created_children}
        for created_node, prereq_titles in zip(created_children, child_prereqs):
            if not prereq_titles:
                continue
            resolved = [
                title_to_id[t]
                for t in prereq_titles
                if t in title_to_id and title_to_id[t] != str(created_node.get("id"))
            ]
            resolved = list(dict.fromkeys(resolved))
            if resolved:
                self.java_client.update_tree_node(str(created_node.get("id")), {"prerequisiteIds": resolved})
        return nodes

    @staticmethod
    def _child_payload(tree_id: str, node_id: str, child: Dict[str, Any], idx: int) -> Dict[str, Any]:
        relevance_score = clamp_metric(child.get("relevanceScore") or child.get("relevance_score") or 2)
        return {
            "treeId": tree_id,
            "parentId": node_id,
            "title": str(child.get("title", f"子节点 {idx + 1}")).strip()[:50],
            "summary": str(child.get("summary", ""))[:160],
            "content": child.get("content", child.get("summary", "")),
            "status": child.get("status", "pending"),
            "importance": clamp_metric(child.get("importance", 2)),
            "relevance": 1 if relevance_score >= 3 else 0,
            "relevanceScore": relevance_score,
            "difficulty": clamp_metric(child.get("difficulty", 2)),
            "depth": child.get("depth"),
            "sortOrder": child.get("sortOrder", idx),
            "prerequisiteIds": child.get("prerequisiteIds", []),
            "collapsed": child.get("collapsed", False),
        }

    @staticmethod
    def _coerce_children(result: Any) -> List[Dict[str, Any]]:
        if isinstance(result, dict):
            # 只取顶层 children，忽略 middle_title 等分组字段
            children = result.get("children", [])
        elif isinstance(result, list):
            children = result
        else:
            children = []
        return [child for child in children if isinstance(child, dict) and child.get("title")]

    def _dedup_and_calibrate(
        self,
        children: List[Dict[str, Any]],
        node_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """对子节点做跨树模糊去重 + 相关度分布校准。

        1. 收集已存在的 title 集合（整棵树）
        2. 过滤掉与已有节点近似重复的子节点
        3. 对保留下来的子节点做相关度分布校准
        """
        existing_titles = self._collect_existing_titles(node_context)
        taken: set[str] = set(existing_titles)
        deduped: List[Dict[str, Any]] = []
        for child in children:
            title = str(child.get("title") or "").strip()[:50]
            if not title:
                continue
            if self._looks_similar_enhanced(title, taken):
                continue
            taken.add(title)
            # 钳制指标到 1-3 范围
            child["importance"] = clamp_metric(child.get("importance", 2))
            child["relevance_score"] = clamp_metric(
                child.get("relevanceScore") or child.get("relevance_score") or 2
            )
            child["relevanceScore"] = child["relevance_score"]
            child["relevance"] = 1 if child["relevance_score"] >= 3 else 0
            child["difficulty"] = clamp_metric(child.get("difficulty", 2))
            deduped.append(child)
        return calibrate_relevance_distribution(deduped)

    def _dedup_angle_groups(
        self,
        groups: List[Dict[str, Any]],
        node_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """跨 group 去重：保证不同角度下不出现近似重复的子节点。"""
        existing_titles = self._collect_existing_titles(node_context)
        taken: set[str] = set(existing_titles)
        for group in groups:
            deduped_children: List[Dict[str, Any]] = []
            for child in group.get("children", []):
                title = str(child.get("title") or "").strip()[:50]
                if not title or self._looks_similar_enhanced(title, taken):
                    continue
                taken.add(title)
                # 钳制指标
                child["importance"] = clamp_metric(child.get("importance", 2))
                child["relevance_score"] = clamp_metric(
                    child.get("relevanceScore") or child.get("relevance_score") or 2
                )
                child["relevanceScore"] = child["relevance_score"]
                child["relevance"] = 1 if child["relevance_score"] >= 3 else 0
                child["difficulty"] = clamp_metric(child.get("difficulty", 2))
                deduped_children.append(child)
            group["children"] = calibrate_relevance_distribution(deduped_children)
        return groups

    def _dedup_principles(
        self,
        principles: List[Dict[str, Any]],
        taken_titles: set[str],
    ) -> List[Dict[str, Any]]:
        """第一性原理去重：过滤掉与已有节点近似重复的原理节点。"""
        deduped: List[Dict[str, Any]] = []
        for child in principles:
            title = str(child.get("title") or "").strip()[:50]
            if not title or self._looks_similar_enhanced(title, taken_titles):
                continue
            taken_titles.add(title)
            deduped.append(child)
        return deduped

    @staticmethod
    def _collect_existing_titles(node_context: Dict[str, Any]) -> List[str]:
        """收集整棵树的已有节点 title，用于跨树去重。"""
        titles: List[str] = []
        tree = node_context.get("tree", {}) or {}
        nodes = tree.get("nodes", []) if isinstance(tree, dict) else []
        # tree 里可能没有 nodes，从 node_context 的其他字段收集
        node = node_context.get("node", {})
        if node.get("title"):
            titles.append(str(node["title"]))
        parent = node_context.get("parent", {})
        if parent and parent.get("title"):
            titles.append(str(parent["title"]))
        for sibling in node_context.get("siblings", []):
            if sibling.get("title"):
                titles.append(str(sibling["title"]))
        for child in node_context.get("children", []):
            if child.get("title"):
                titles.append(str(child["title"]))
        # 从完整节点列表收集（如果 _build_node_context 返回了所有节点）
        all_nodes = node_context.get("all_nodes", [])
        for n in all_nodes:
            if isinstance(n, dict) and n.get("title"):
                titles.append(str(n["title"]))
        # 从 tree 对象的 nodes 字段收集
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict) and n.get("title"):
                    titles.append(str(n["title"]))
        return titles

    @staticmethod
    def _dedup_title(title: str, taken: set[str]) -> str:
        """如果 title 与已有节点重复，追加序号使其唯一。"""
        if not _looks_similar(title, taken):
            return title
        base = title[:45]
        for i in range(2, 100):
            candidate = f"{base}({i})"
            if not _looks_similar(candidate, taken):
                return candidate
        return f"{base}_{id(title)}"

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
    def _parent_depth(node_context: Dict[str, Any]) -> int:
        return int((node_context.get("node") or {}).get("depth") or 0)

    @classmethod
    def _remaining_depth(cls, parent_depth: int) -> int:
        return max(0, MAX_TREE_DEPTH - parent_depth)

    @classmethod
    def _subdivide_depth_error(cls, node_context: Dict[str, Any]) -> Optional[str]:
        if cls._parent_depth(node_context) >= MAX_TREE_DEPTH:
            return (
                "知识树已达最深层（主模块 → 细分知识点 → 最细知识点），"
                "当前节点无法继续拆分。"
            )
        return None

    @staticmethod
    def _depth_caution(depth: int, node_title: str) -> Optional[Dict[str, str]]:
        """深度自适应 caution 兜底：LLM 未给出 caution 时本地补充。"""
        if depth <= 1:
            return None
        if depth == 2:
            return {
                "label": "粒度提醒",
                "rationale": f"「{node_title}」已经比较具体，继续拆分可能产生过于细碎的知识点。",
            }
        return {
            "label": "深度警告",
            "rationale": "当前层级已经很深，建议回到上层节点继续学习主线。",
        }

    def _domain_guardrail_text(self, node_context: Dict[str, Any]) -> str:
        tree = node_context.get("tree", {}) or {}
        node = node_context.get("node", {}) or {}
        field = str(tree.get("field") or "").strip()
        plan_title = str(tree.get("title") or "").strip()
        bg = str(tree.get("learningBackground") or "").strip()
        domain = field or plan_title or str(node.get("title") or "").strip() or "当前学习计划"
        bg_line = f"学习背景：{bg}。" if bg else ""
        return (
            "\n\n【领域边界-必须遵守】"
            f"用户学习目标领域：{domain}。{bg_line}"
            "子节点必须直接服务于该领域的工程/业务实践，帮助用户完成当前学习计划。"
            "禁止泛化到无关基础学科（如把线束/harness 工程拆成物理、化学、材料学公理或大学理工目录）。"
            "前置知识只保留本领域直接相关的最小必要概念（如标准规范、材料规格、工艺步骤、图纸要素）。"
            "宁可少拆、拆准，也不要偏题扩题。"
        )

    @staticmethod
    def _depth_limit_text(node_context: Dict[str, Any]) -> str:
        depth = KnowledgeTreeAiService._parent_depth(node_context)
        remaining = KnowledgeTreeAiService._remaining_depth(depth)
        return (
            "\n\n【层级限制】知识树为 3 层子节点："
            "主模块(depth=1) → 细分知识点(depth=2) → 最细知识点(depth=3)。"
            "每次拆分只产一层 children，直接挂在当前节点下，不要建中间分组。"
            f"当前节点深度={depth}，最多还能向下拆 {remaining} 层。"
        )

    @staticmethod
    def _split_preview_title(angle: str, current_title: str) -> str:
        """拆分预览标题（仅用于 SSE 展示，不创建分组节点）。"""
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
            # 钳制每个 child 的指标
            for child in children:
                child["importance"] = clamp_metric(child.get("importance", 2))
                child["relevanceScore"] = clamp_metric(
                    child.get("relevanceScore") or child.get("relevance_score") or 2
                )
                child["relevance_score"] = child["relevanceScore"]
                child["relevance"] = 1 if child["relevanceScore"] >= 3 else 0
                child["difficulty"] = clamp_metric(child.get("difficulty", 2))
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
            if group and group.get("children"):
                normalized.append(group)
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
        if tree.get("learningBackground"):
            parts.append(f"学习背景：{tree.get('learningBackground')}")
        parts.extend([
            f"当前节点：{node.get('title') or node.get('id')}",
            f"节点摘要：{node.get('summary') or '无'}",
            f"节点内容：{node.get('content') or '无'}",
            f"节点路径：{node_context.get('path') or node.get('title') or node.get('id')}",
            f"兄弟节点：{self._node_list_text(node_context.get('siblings', []))}",
            f"已有子节点：{self._node_list_text(node_context.get('children', []))}",
            f"已有树路径：{self._existing_paths_text(node_context)}",
            f"最近对话：{self._message_list_text(node_context.get('messages', []))}",
        ])
        return "\n".join(parts)

    def _existing_paths_text(self, node_context: Dict[str, Any]) -> str:
        """收集整棵树的已有节点 title；节点过多时本地粗筛截断。"""
        all_nodes = node_context.get("all_nodes", [])
        if not all_nodes:
            return "无"
        node = node_context.get("node", {}) or {}
        query = " ".join(part for part in [node.get("title"), node.get("summary")] if part)
        if len(all_nodes) > RANK_PREFILTER_MAX and query:
            filtered = _prefilter_nodes_by_query(all_nodes, query, RANK_PREFILTER_MAX)
        else:
            filtered = all_nodes
        titles = [str(n["title"]) for n in filtered if isinstance(n, dict) and n.get("title")]
        if not titles:
            return "无"
        if len(all_nodes) > len(titles):
            return "；".join(titles) + f" ...(共 {len(all_nodes)} 个，已截断展示)"
        return "；".join(titles)

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

    def _explain_prompt(
        self,
        tree_id: str,
        node_id: str,
        message: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
    ) -> str:
        return (
            f"tree_id={tree_id}, node_id={node_id}\n用户问题：{message}\n\n"
            f"节点上下文：\n{self._node_context_text(node_context)}\n\n"
            f"可参考资料：\n{self._context_text(context_chunks)}"
        )

    def _tree_meta(self, node_context: Dict[str, Any]) -> Dict[str, str]:
        tree = node_context.get("tree", {}) or {}
        return {
            "field": str(tree.get("field") or ""),
            "current_problem": str(tree.get("currentProblem") or ""),
            "learning_background": str(tree.get("learningBackground") or ""),
        }

    def _subdivide_prompt_dict(
        self,
        node_id: str,
        angle: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:
        meta = self._tree_meta(node_context)
        return {
            "task": "knowledge_tree_subdivide",
            "instructions": self._subdivide_prompt(node_id, angle, context_chunks, node_context, mode),
            "json_schema": {
                "children": [{"title": "string", "summary": "string", "importance": 2, "relevanceScore": 2, "difficulty": 2, "prerequisite_titles": []}],
            },
            **meta,
            "node_id": node_id,
            "angle": angle or "按学习顺序",
            "mode": self._normalize_mode(mode),
            "target_range": self._target_range_for_mode(mode),
            "node_context": self._node_context_text(node_context),
            "materials": self._context_text(context_chunks),
        }

    def _subdivision_options_prompt_dict(
        self,
        node_id: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:
        meta = self._tree_meta(node_context)
        return {
            "task": "knowledge_tree_subdivision_options",
            "instructions": self._subdivision_options_prompt(node_id, context_chunks, node_context, mode),
            "json_schema": {"options": [{"angle": "string", "label": "string", "rationale": "string"}], "caution": {"label": "string", "rationale": "string"}},
            **meta,
            "node_id": node_id,
            "mode": self._normalize_mode(mode),
            "target_range": self._target_range_for_mode(mode),
            "node_context": self._node_context_text(node_context),
            "materials": self._context_text(context_chunks),
        }

    def _multi_angle_prompt_dict(
        self,
        node_id: str,
        angles: List[Dict[str, str]],
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:
        meta = self._tree_meta(node_context)
        return {
            "task": "knowledge_tree_multi_angle",
            "instructions": self._multi_angle_prompt(node_id, angles, context_chunks, node_context, mode),
            "json_schema": {"groups": [{"angle": "string", "label": "string", "children": []}]},
            **meta,
            "node_id": node_id,
            "angles": angles,
            "mode": self._normalize_mode(mode),
            "target_range": self._target_range_for_mode(mode),
            "node_context": self._node_context_text(node_context),
            "materials": self._context_text(context_chunks),
        }

    def _first_principles_prompt_dict(
        self,
        node_id: str,
        context_chunks: List[Dict[str, Any]],
        node_context: Dict[str, Any],
        mode: str,
        parent: Optional[Dict[str, Any]] = None,
        path: str = "",
        rel_depth: int = 0,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        parent = parent or node_context.get("node", {})
        meta = self._tree_meta(node_context)
        return {
            "task": "knowledge_tree_first_principles",
            "instructions": self._first_principles_prompt(node_id, context_chunks, node_context, mode, parent, path, rel_depth, max_depth),
            "json_schema": {"is_fundamental": False, "children": []},
            **meta,
            "node_id": node_id,
            "rel_depth": rel_depth,
            "max_depth": max_depth,
            "parent_title": parent.get("title") or parent.get("id"),
            "path": path or node_context.get("path"),
            "node_context": self._node_context_text(node_context),
            "materials": self._context_text(context_chunks),
        }

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
            f"模式：{self._normalize_mode(mode)}，目标数量：{self._target_range_for_mode(mode)} 个子节点。"
            f"{self._depth_limit_text(node_context)}"
            f"{self._domain_guardrail_text(node_context)}"
            "\n\n【拆分规则 — 每次只产一层 children】"
            "  - children 直接挂在当前节点下，不要建中间分组"
            "  - 根据当前节点的性质决定 children 的粒度："
            "    * 分类/总结/全景图类节点 → children 是细分知识点（子分类项，如 Jedis/Lettuce/Redisson）"
            "    * 流程/步骤类节点 → children 是阶段或步骤"
            "    * 已经足够具体的细分知识点 → children 是最细知识点（如 连接管理/数据结构操作）"
            "  - 不要一次拆两层，每次只产一层 children"
            "  - 禁止输出 middle_title 或嵌套结构"
            "\n【children 规则】"
            "  - 每个 child 必须服务于用户的学习目标，围绕当前节点的独特视角展开。"
            "  - children title 在语义上不得与已有树路径中任何一个节点重复或近似。"
            "    这条比'拆得全'更重要——宁可少给一个，也不要重复。"
            "  - 每个 child 包含 importance、relevanceScore、difficulty（1-3），summary 一句话（不超 80 字）。"
            "  - relevanceScore=3 只给能直接回答用户当前追问的；弱相关用 1-2。"
            "  - 如果某个 child 依赖同组兄弟节点才能理解，在 prerequisite_titles 里写出依赖的兄弟 title。"
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
        tree = node_context.get("tree", {}) or {}
        field = str(tree.get("field") or tree.get("title") or "新的学习主题")
        current_problem = str(tree.get("currentProblem") or tree.get("title") or "")
        node_title = str(parent.get("title") or node_id)
        node_summary = str(parent.get("summary") or "未提供")
        node_path = path or str(node_context.get("path") or node_title)
        return (
            "你在用【第一性原理】拆解一个知识点，目标是找出「要真正理解它，必须先掌握的更底层依赖」。"
            f"\n整体学习主题：{field}"
            f"\n用户当前问题：{current_problem or '未说明'}"
            f"\n当前要拆解的知识点：{node_title}"
            f"\n这个知识点的说明：{node_summary}"
            f"\n它在知识树里的路径(从根到它)：{node_path}"
            f"\n当前相对深度(起点=0)：{rel_depth}，最大相对深度：{max_depth}"
            f"{self._depth_limit_text(node_context)}"
            "\n\n请回答：要从第一性原理理解「"
            f"{node_title}」，必须先掌握哪些更底层的前置知识？"
            "\n\n【硬规则】"
            "  - 只列真正更底层、更基础的前置依赖——是它的「地基」，不是它的「应用」或「分支」「例子」。"
            "  - 数量：1 到 3 个。宁可少而准，不要凑数。"
            "  - 每个底层依赖比当前知识点更基础、更通用、更接近公理或基础学科。"
            "  - 如果当前知识点已经是基础学科的公理/最小单位，返回空 children 并设 is_fundamental=true。"
            "  - 已经在路径里出现过的知识点不要再列（避免兜圈子）。"
            "\n\n【输出字段】每个底层依赖必须包含："
            "  - title：≤ 20 字，明确的基础知识点/学科概念"
            "  - summary：≤ 60 字，说明它是什么以及为什么它是上层知识的地基"
            "  - relation / fpRelation：≤ 30 字，与当前节点的知识关联类型"
            "  - why / fpReason：≤ 120 字，用第一性原理解释因果链，不要只说「很重要」"
            "  - isFundamental：该依赖本身是否已是不可再拆的基础公理/最小单位"
            f"\n模式：{self._normalize_mode(mode)}。"
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
        node = node_context.get("node", {}) or {}
        depth = int(node.get("depth") or self._parent_depth(node_context))
        return (
            f"请为知识树节点 node_id={node_id} 推荐 3 个适合继续拆分的角度。"
            "\n\n【语气硬约束】rationale 字段必须用第二人称「你」，"
            "禁止用「用户」「该用户」「他/她」等第三人称。"
            "\n\n【维度库参考（可混合使用）】"
            "\n  - 构成/组成：这个节点由哪几部分组成"
            "\n  - 步骤/流程：做这件事的先后顺序"
            "\n  - 类型/分类：这个东西有哪几种"
            "\n  - 对比/异同：和另一个东西的差异轴"
            "\n  - 因果/驱动：为什么会出现这个结果"
            "\n  - 指标/评估：用什么标准衡量好坏"
            "\n  - 场景/用例：在什么情况下会用到"
            "\n  - 风险/失败模式：常见的坑和踩雷点"
            "\n  - 角色/立场：不同身份的人怎么看"
            "\n\n【选角度的依据】"
            "\n  - 节点本身性质（分类/总结 vs 流程 vs 具体概念）"
            "\n  - 分类/总结类节点优先推荐「按子类型分」「按技术栈分」，不要直接推荐「按具体实现分」"
            "\n  - 最近对话里聊到的方向，避开已经聊透的角度"
            "\n  - 不要重复已有子节点体现的角度"
            "\n  - 学习背景：新手优先'构成/分类/场景'；有经验者可推荐'因果/指标/风险'"
            "\n\n【每个 option 包含】"
            "\n  - angle：角度短词（中文，最多 6 字，例如'类型分类'、'步骤流程'）"
            "\n  - label：用户视角的标题（8-14 字，例如'按几种类型分'）"
            "\n  - rationale：为什么这个角度合适（1 句话不超 40 字，带具体词）"
            f"\n\n【caution 规则 — 当前节点深度 depth = {depth}】"
            "\n  你必须主动判断要不要给 caution："
            "\n    * depth <= 1：基本让用户拆，很少给 caution"
            "\n    * depth == 2：需要警觉，再拆一层就到最深层"
            "\n    * depth >= 3：几乎一定给 caution"
            "\n  caution 触发条件（任一即可）："
            "\n    * 节点已经偏离学习目标，继续拆会绕远路"
            "\n    * depth 已经偏深，再拆边际收益很低"
            "\n    * 节点本身就是单点事实或具体实例"
            "\n    * 最近对话能看出用户已经把节点聊得差不多了"
            f"\n\n模式：{self._normalize_mode(mode)}，目标数量：{self._target_range_for_mode(mode)} 个子节点。"
            f"{self._domain_guardrail_text(node_context)}"
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
            f"{self._depth_limit_text(node_context)}"
            f"{self._domain_guardrail_text(node_context)}"
            "\n\n【拆分规则 — 每次只产一层 children】"
            "  - children 直接挂在当前节点下，不要建中间分组层"
            "  - 根据节点性质决定 children 粒度：分类/总结节点产出细分知识点，具体节点产出最细知识点"
            "  - 每个角度最多 2 个子节点，且必须属于用户学习领域"
            "\n\n【跨 group 去重规则】"
            "  - 不同 group 下的 children title 不得重复或近似。"
            "  - children title 也不得与已有树路径中任何节点重复或近似。"
            "  - 这条比'拆得全'更重要——宁可少给一个，也不要重复。"
            "\n\n【children 规则】"
            "  - 每个 child 包含 importance、relevanceScore、difficulty（1-3），summary 一句话（不超 80 字）。"
            "  - relevanceScore=3 只给能直接回答用户当前追问的；弱相关用 1-2。"
            f"模式：{self._normalize_mode(mode)}，每组目标数量：{self._target_range_for_mode(mode)} 个子节点。"
            "\n\n节点上下文：\n"
            f"{self._node_context_text(node_context)}"
            f"\n参考资料：\n{self._context_text(context_chunks)}"
        )

    def _quiz_prompt(self, node_id: str, plan_id: int, context_chunks: List[Dict[str, Any]], node_context: Dict[str, Any]) -> str:
        node = node_context.get("node", {}) or {}
        return (
            f"请为 plan_id={plan_id}, node_id={node_id} 生成 3 道测验题。\n"
            f"节点：{node.get('title') or node_id}\n"
            f"摘要：{node.get('summary') or '无'}\n\n"
            f"资料：\n{self._context_text(context_chunks)}"
        )

    def _flashcards_prompt(self, node_id: str, context_chunks: List[Dict[str, Any]], node_context: Dict[str, Any]) -> str:
        node = node_context.get("node", {}) or {}
        return (
            f"请为 node_id={node_id} 生成 5 张闪卡。\n"
            f"节点：{node.get('title') or node_id}\n"
            f"摘要：{node.get('summary') or '无'}\n\n"
            f"资料：\n{self._context_text(context_chunks)}"
        )

    @staticmethod
    def _children_json_system_prompt() -> str:
        return (
            "你是知识树拆分助手。严格输出 JSON，不输出 Markdown。\n"
            "输出格式：{\"children\":[{\"title\":\"子节点标题\",\"summary\":\"一句话说明\","
            "\"importance\":2,\"relevanceScore\":2,\"difficulty\":2,"
            "\"prerequisite_titles\":[]}]}。\n"
            "每次只输出一层 children，不要输出 middle_title 或嵌套结构。"
            "importance/relevanceScore/difficulty 范围 1-3。"
            "relevanceScore=3 只给能直接回答用户当前追问的子节点。"
            "prerequisite_titles 是同组兄弟节点的 title 列表，表示学习当前节点前需要先学哪些兄弟节点。"
        )

    @staticmethod
    def _subdivision_options_json_system_prompt() -> str:
        return (
            "严格输出 JSON，不输出 Markdown："
            "{\"options\":[{\"angle\":\"类型分类\",\"label\":\"按几种类型分\","
            "\"rationale\":\"用第二人称描述为什么适合\"}],"
            "\"caution\":{\"label\":\"粒度提醒\",\"rationale\":\"用第二人称描述为什么不建议拆\"}}。"
            "只返回 2 到 4 个拆分角度。每个角度必须能生成并列的学习子节点。"
            "rationale 用第二人称「你」描述，禁止用第三人称指代提问者。"
            "caution 按深度档位主动判断是否给出，不是默认 null。"
        )

    @staticmethod
    def _multi_angle_json_system_prompt() -> str:
        return (
            "严格输出 JSON，不输出 Markdown：{\"groups\":[{\"angle\":\"by_concept\","
            "\"label\":\"按概念拆\",\"rationale\":\"拆分理由\","
            "\"children\":[{\"title\":\"子知识点\",\"summary\":\"说明\","
            "\"importance\":3,\"relevanceScore\":2,\"difficulty\":2,"
            "\"prerequisite_titles\":[]}]}]}。"
            "每个 group 对应用户给定的一个角度，每组 children 最多 2 个。"
            "importance/relevanceScore/difficulty 范围 1-3。"
            "children 必须属于用户当前学习领域，禁止物理/化学/材料学公理。"
            "不同 group 下的 children title 不得重复或近似。"
        )

    @staticmethod
    def _first_principles_json_system_prompt() -> str:
        return (
            "你是第一性原理拆解助手。严格输出 JSON，不输出 Markdown："
            "{\"is_fundamental\":false,"
            "\"children\":[{\"title\":\"底层前置知识\",\"summary\":\"为什么它是上层的地基\","
            "\"relation\":\"知识关联类型\",\"why\":\"为什么必须从上层拆到这里\","
            "\"fpRelation\":\"知识关联类型\",\"fpReason\":\"为什么必须从上层拆到这里\","
            "\"importance\":2,\"difficulty\":2,"
            "\"isFundamental\":false}]}。"
            "只列真正更底层、更基础的前置依赖（地基，不是应用或例子）。"
            "数量 1-3 个，宁可少而准不要凑数。"
            "如果当前知识点已是基础公理/最小单位，返回空 children 并设 is_fundamental=true。"
        )


def get_knowledge_tree_ai_service() -> KnowledgeTreeAiService:
    return KnowledgeTreeAiService()
