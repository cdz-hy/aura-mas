from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class KnowledgeTreeAiEvent(BaseModel):
    type: str
    node_id: Optional[str] = None
    content: Optional[str] = None
    data: Optional[Any] = None
    message: Optional[Dict[str, Any]] = None
    nodes: Optional[List[Dict[str, Any]]] = None
