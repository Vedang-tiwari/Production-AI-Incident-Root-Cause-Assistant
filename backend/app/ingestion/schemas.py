from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    LOG = "log"
    ERROR = "error"
    METRIC = "metric"
    DEPLOYMENT = "deployment"
    OTEL = "otel"
    INFRASTRUCTURE = "infrastructure"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    TRIGGERED = "triggered"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    RESOLVED = "resolved"
    CLOSED = "closed"


class LogIngestRequest(BaseModel):
    service: str
    environment: str = "production"
    message: str
    level: str = "info"  # debug, info, warn, error, fatal
    timestamp: Optional[datetime] = Field(default_factory=get_utc_now)
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorIngestRequest(BaseModel):
    service: str
    environment: str = "production"
    error_class: str
    error_message: str
    stack_trace: Optional[str] = None
    http_status: Optional[int] = None
    timestamp: Optional[datetime] = Field(default_factory=get_utc_now)
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricIngestRequest(BaseModel):
    service: str
    environment: str = "production"
    metric_name: str  # e.g. "db_pool_utilization", "latency_ms", "cpu_percent", "error_rate"
    value: float
    unit: str = "count"
    timestamp: Optional[datetime] = Field(default_factory=get_utc_now)
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class DeploymentIngestRequest(BaseModel):
    service: str
    environment: str = "production"
    version: str
    commit_hash: Optional[str] = None
    author: Optional[str] = None
    status: str = "completed"  # started, completed, failed, rolled_back
    timestamp: Optional[datetime] = Field(default_factory=get_utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OTelSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: Optional[str] = "SERVER"
    status_code: str = "OK"  # OK, ERROR, UNSET
    status_message: Optional[str] = None
    start_time: Optional[datetime] = Field(default_factory=get_utc_now)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class OTelIngestRequest(BaseModel):
    service: str
    environment: str = "production"
    spans: List[OTelSpan] = Field(default_factory=list)
    resource_attributes: Dict[str, Any] = Field(default_factory=dict)


class BatchIngestRequest(BaseModel):
    events: List[Dict[str, Any]] = Field(default_factory=list)


class NormalizedEvent(BaseModel):
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=get_utc_now)
    service: str
    environment: str = "production"
    event_type: EventType
    severity: Severity = Severity.INFO
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    incident_id: Optional[str] = None

