import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas.knowledge_tree import KnowledgeTreeAiEvent
from app.schemas.sse_bridge import _sse
from app.services.db.java_client import java_client
from app.services.knowledge_tree_ai import get_knowledge_tree_ai_service

logger = logging.getLogger("api.knowledge_tree")
router = APIRouter()


def _user_id_from_ticket(ticket: str) -> int:
    try:
        ticket_info = java_client.validate_ticket(ticket)
        return ticket_info["user_id"]
    except Exception as exc:
        logger.warning("知识树鉴权失败: %s", exc)
        raise HTTPException(status_code=401, detail=str(exc))


async def _event_stream(events) -> AsyncGenerator[str, None]:
    async for event in events:
        KnowledgeTreeAiEvent(**event)
        yield _sse(event)


def _verify_node_access(tree_id: str, node_id: str, user_id: int) -> None:
    try:
        java_client.verify_tree_node_access(tree_id, node_id, user_id)
    except Exception as exc:
        logger.warning("节点访问校验失败: tree=%s node=%s user=%s error=%s", tree_id, node_id, user_id, exc)
        raise HTTPException(status_code=404, detail=str(exc))


def _verify_plan_tree_access(plan_id: int, tree_id: str, user_id: int) -> None:
    try:
        tree_response = java_client.get_tree_by_plan(plan_id, user_id)
    except Exception as exc:
        logger.warning("计划树访问校验失败: plan=%s tree=%s user=%s error=%s", plan_id, tree_id, user_id, exc)
        raise HTTPException(status_code=404, detail=str(exc))

    tree = tree_response.get("tree", {}) if isinstance(tree_response, dict) else {}
    if tree.get("id") != tree_id:
        logger.warning("树不属于计划: tree=%s plan=%s", tree_id, plan_id)
        raise HTTPException(status_code=404, detail="tree does not belong to plan")


@router.get("/tree/plan/{plan_id}/ensure")
async def ensure_tree(plan_id: int, ticket: str = Query(...)):
    user_id = _user_id_from_ticket(ticket)
    logger.info("知识树确保: plan=%s user=%s", plan_id, user_id)
    return java_client.get_or_create_tree(plan_id, user_id)


@router.get("/tree/plan/{plan_id}/bootstrap")
async def bootstrap_tree(
    plan_id: int,
    tree_id: str = Query(...),
    ticket: str = Query(...),
    mode: str = Query("Lite"),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_plan_tree_access(plan_id, tree_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.bootstrap_tree(
            user_id=user_id,
            plan_id=plan_id,
            tree_id=tree_id,
            mode=mode,
        )),
        media_type="text/event-stream",
    )


@router.get("/tree/plan/{plan_id}/preview-topics")
async def preview_topics(
    plan_id: int,
    tree_id: str = Query(...),
    ticket: str = Query(...),
    mode: str = Query("Lite"),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_plan_tree_access(plan_id, tree_id, user_id)
    service = get_knowledge_tree_ai_service()
    topics = await service.preview_topics(user_id, plan_id, tree_id, mode)
    return {"topics": topics}


@router.get("/tree/plan/{plan_id}/grow-children")
async def grow_children(
    plan_id: int,
    tree_id: str = Query(...),
    ticket: str = Query(...),
    mode: str = Query("Lite"),
    topics_override: str = Query(None),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_plan_tree_access(plan_id, tree_id, user_id)
    service = get_knowledge_tree_ai_service()
    parsed = None
    if topics_override:
        try:
            parsed = json.loads(topics_override)
        except json.JSONDecodeError:
            pass
    return StreamingResponse(
        _event_stream(service.grow_children_stream(
            user_id=user_id,
            tree_id=tree_id,
            mode=mode,
            topics_override=parsed,
        )),
        media_type="text/event-stream",
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/explain")
async def explain_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    message: str = Query(...),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.explain_node(user_id=user_id, tree_id=tree_id, node_id=node_id, message=message)),
        media_type="text/event-stream",
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/subdivide")
async def subdivide_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    angle: str = Query(""),
    mode: str = Query("Lite"),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.subdivide_node(user_id=user_id, tree_id=tree_id, node_id=node_id, angle=angle, mode=mode)),
        media_type="text/event-stream",
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/subdivision-options")
async def subdivision_options(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    mode: str = Query("Lite"),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return await service.suggest_subdivision_options(
        user_id=user_id,
        tree_id=tree_id,
        node_id=node_id,
        mode=mode,
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/multi-angle-subdivide")
async def multi_angle_subdivide_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    angles: str = Query("[]"),
    mode: str = Query("Lite"),
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
            mode=mode,
        )),
        media_type="text/event-stream",
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/first-principles")
async def first_principles_node(
    request: Request,
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    mode: str = Query("Lite"),
    max_depth: int = Query(6),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.first_principles(
            user_id=user_id,
            tree_id=tree_id,
            node_id=node_id,
            mode=mode,
            max_depth=max(1, min(int(max_depth), 10)),
            is_disconnected=request.is_disconnected,
        )),
        media_type="text/event-stream",
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/quiz")
async def quiz_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    plan_id: int = Query(...),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    _verify_plan_tree_access(plan_id, tree_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.quiz_node(user_id=user_id, tree_id=tree_id, node_id=node_id, plan_id=plan_id)),
        media_type="text/event-stream",
    )


@router.get("/tree/{tree_id}/nodes/{node_id}/flashcards")
async def flashcards_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
    plan_id: int = Query(...),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    _verify_plan_tree_access(plan_id, tree_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.flashcards_node(user_id=user_id, tree_id=tree_id, node_id=node_id, plan_id=plan_id)),
        media_type="text/event-stream",
    )
