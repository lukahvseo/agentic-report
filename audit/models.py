from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


AuditStatus = Literal["pass", "warning", "fail", "unknown"]
Severity = Literal["low", "medium", "high", "critical"]
Confidence = Literal["low", "medium", "high"]


class Evidence(BaseModel):
    url: Optional[str] = None
    signal: str
    details: Optional[str] = None
    raw: Optional[Any] = None


class AuditFinding(BaseModel):
    check_id: str
    category: str
    title: str
    status: AuditStatus
    severity: Severity
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)
    affected_urls_count: int = 0
    recommendation: str
    business_impact: str
    priority_score: float = 0.0


class PageFetchResult(BaseModel):
    url: str
    final_url: str
    status_code: Optional[int]
    redirect_chain: list[str] = Field(default_factory=list)
    html: Optional[str] = None
    content_type: Optional[str] = None
    response_length: int = 0
    server: Optional[str] = None
    x_robots_tag: Optional[str] = None
    error: Optional[str] = None


class PageSignals(BaseModel):
    url: str
    final_url: str
    status_code: Optional[int]

    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1s: list[str] = Field(default_factory=list)
    canonicals: list[str] = Field(default_factory=list)
    meta_robots: Optional[str] = None

    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)

    schema_types: list[str] = Field(default_factory=list)
    schema_data: dict = Field(default_factory=dict)
    tracking_signals: list[str] = Field(default_factory=list)

    page_type: str = "unknown"
    body_text_sample: Optional[str] = None

    redirect_chain: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class AuditResult(BaseModel):
    input_url: str
    final_url: Optional[str] = None
    pages_checked: int = 0
    findings: list[AuditFinding] = Field(default_factory=list)
    page_signals: list[PageSignals] = Field(default_factory=list)