from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetrievedItem:
    source_type: str
    source: str
    query_key: str
    title: str
    url: str
    content: str
    published_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgedDataset:
    query: str
    items: List[RetrievedItem]
    dropped_count: int
    guardrail_flags: List[str] = field(default_factory=list)
    judge_notes: List[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    summary: str
    key_findings: List[str]
    risks: List[str]
    recommendations: List[str]
    confidence_score: float
    sections: Dict[str, Any]