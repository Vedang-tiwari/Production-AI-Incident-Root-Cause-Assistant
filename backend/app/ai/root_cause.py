from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SupportingEvidenceItem(BaseModel):
    id: str
    type: str  # log, metric, deployment, otel, anomaly
    timestamp: Optional[str] = None
    source: str
    summary: str


class RootCauseHypothesis(BaseModel):
    title: str
    likelihood: str  # High, Medium, Low
    confidence_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)


class RecommendedRemediation(BaseModel):
    action: str  # rollback, restart, scale_pool, config_fix, create_jira
    risk_level: str  # Low, Medium, High, Critical
    description: str
    requires_approval: bool = True
    command_or_script: Optional[str] = None


class InvestigationReportOutput(BaseModel):
    summary: str
    hypotheses: List[RootCauseHypothesis]
    supporting_evidence: List[SupportingEvidenceItem]
    recommendations: List[RecommendedRemediation]
    confidence_score: float = Field(ge=0.0, le=1.0)
    uncertainty_factors: List[str] = Field(default_factory=list)

