from typing import List, Optional

from pydantic import BaseModel


class AttackPathNode(BaseModel):
    id: str
    type: str
    label: str
    severity: Optional[str] = None
    risk_score: Optional[int] = None
    finding_id: Optional[str] = None


class AttackPathLink(BaseModel):
    source: str
    target: str
    relationship: str


class AttackPath(BaseModel):
    id: str
    nodes: List[str]
    severity: str


class AttackPathResponse(BaseModel):
    scan_id: str
    nodes: List[AttackPathNode]
    links: List[AttackPathLink]
    paths: List[AttackPath]