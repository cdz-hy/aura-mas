import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas.knowledge_tree import KnowledgeTreeAiEvent
from app.schemas.sse_bridge import _sse
from app.services.db.java_client import java_client
from app.services.knowledge_tree_ai import get_knowledge_tree_ai_service

router = APIRouter()


def _user_id_from_ticket(ticket: str) -> int:
    try:
        ticket_info = java_client.validate_ticket(ticket)
        return ticket_info["user_id"]
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))


async def _event_stream(events) -> AsyncGenerator[str, None]:
    async for event in events:
        KnowledgeTreeAiEvent(**event)
        yield _sse(event)


def _verify_node_access(tree_id: str, node_id: str, user_id: int) -> None:
    try:
        java_client.verify_tree_node_access(tree_id, node_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _verify_plan_tree_access(plan_id: int, tree_id: str, user_id: int) -> None:
    try:
        tree_response = java_client.get_tree_by_plan(plan_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    tree = tree_response.get("tree", {}) if isinstance(tree_response, dict) else {}
    if tree.get("id") != tree_id:
        raise HTTPException(status_code=404, detail="tree does not belong to plan")


@router.get("/tree/plan/{plan_id}/ensure")
async def ensure_tree(plan_id: int, ticket: str = Query(...)):
    user_id = _user_id_from_ticket(ticket)
    return java_client.get_or_create_tree(plan_id, user_id)


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
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.subdivide_node(user_id=user_id, tree_id=tree_id, node_id=node_id, angle=angle)),
        media_type="text/event-stream",
    )


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


@router.get("/tree/{tree_id}/nodes/{node_id}/first-principles")
async def first_principles_node(
    tree_id: str,
    node_id: str,
    ticket: str = Query(...),
):
    user_id = _user_id_from_ticket(ticket)
    _verify_node_access(tree_id, node_id, user_id)
    service = get_knowledge_tree_ai_service()
    return StreamingResponse(
        _event_stream(service.first_principles(user_id=user_id, tree_id=tree_id, node_id=node_id)),
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
