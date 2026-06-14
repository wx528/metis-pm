from typing import List, Optional, Dict
from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    type: str
    title: str
    issue_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    issue_type: Optional[str] = None
    labels: Optional[List[str]] = None
    milestone_id: Optional[int] = None
    parent_id: Optional[int] = None
    size: int = 12
    color: str = "#888888"
    opacity: float = 1.0


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    labels: Dict[str, str]
