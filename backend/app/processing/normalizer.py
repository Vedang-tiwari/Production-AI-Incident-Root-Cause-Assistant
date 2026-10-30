from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional
from backend.app.core.logging import logger
from backend.app.db.models import Event
from backend.app.ingestion.schemas import (
    DeploymentIngestRequest,
    ErrorIngestRequest,
    EventType,
    LogIngestRequest,
    MetricIngestRequest,
    NormalizedEvent,
    OTelSpan,
    Severity,
)


def map_log_level_to_severity(level: str) -> Severity:
    lvl = (level or "").lower().strip()
    if lvl in ["fatal", "critical", "panic"]:
        return Severity.CRITICAL
    if lvl in ["error", "err"]:
        return Severity.HIGH
    if lvl in ["warn", "warning"]:
        return Severity.MEDIUM
    if lvl in ["info", "notice"]:
        return Severity.INFO
    return Severity.LOW


class EventNormalizer:
    @staticmethod
    def normalize_log(req: LogIngestRequest) -> NormalizedEvent:
        sev = map_log_level_to_severity(req.level)
        return NormalizedEvent(
            id=str(uuid.uuid4()),
            timestamp=req.timestamp or datetime.now(timezone.utc),
            service=req.service.strip().lower(),
            environment=req.environment.strip().lower(),
            event_type=EventType.LOG,
            severity=sev,
            message=req.message.strip(),
            payload={
                "level": req.level,
                "metadata": req.metadata,
            },
            trace_id=req.trace_id,
            correlation_id=req.correlation_id,
        )

    @staticmethod
    def normalize_error(req: ErrorIngestRequest) -> NormalizedEvent:
        # Default error severity is HIGH or CRITICAL depending on HTTP status
        sev = Severity.HIGH
        if req.http_status and req.http_status >= 500:
            sev = Severity.CRITICAL

        msg = f"[{req.error_class}] {req.error_message}"
        return NormalizedEvent(
            id=str(uuid.uuid4()),
            timestamp=req.timestamp or datetime.now(timezone.utc),
            service=req.service.strip().lower(),
            environment=req.environment.strip().lower(),
            event_type=EventType.ERROR,
            severity=sev,
            message=msg,
            payload={
                "error_class": req.error_class,
                "error_message": req.error_message,
                "stack_trace": req.stack_trace,
                "http_status": req.http_status,
                "metadata": req.metadata,
            },
            trace_id=req.trace_id,
            correlation_id=req.correlation_id,
        )

    @staticmethod
    def normalize_metric(req: MetricIngestRequest) -> NormalizedEvent:
        msg = f"Metric {req.metric_name}: {req.value} {req.unit}"
        return NormalizedEvent(
            id=str(uuid.uuid4()),
            timestamp=req.timestamp or datetime.now(timezone.utc),
            service=req.service.strip().lower(),
            environment=req.environment.strip().lower(),
            event_type=EventType.METRIC,
            severity=Severity.INFO,
            message=msg,
            payload={
                "metric_name": req.metric_name,
                "value": req.value,
                "unit": req.unit,
                "dimensions": req.dimensions,
            },
        )

    @staticmethod
    def normalize_deployment(req: DeploymentIngestRequest) -> NormalizedEvent:
        sev = Severity.INFO
        if req.status == "failed":
            sev = Severity.HIGH
        elif req.status == "rolled_back":
            sev = Severity.MEDIUM

        commit_short = req.commit_hash[:7] if req.commit_hash else "unknown"
        msg = f"Deployment {req.version} ({commit_short}) - Status: {req.status}"
        return NormalizedEvent(
            id=str(uuid.uuid4()),
            timestamp=req.timestamp or datetime.now(timezone.utc),
            service=req.service.strip().lower(),
            environment=req.environment.strip().lower(),
            event_type=EventType.DEPLOYMENT,
            severity=sev,
            message=msg,
            payload={
                "version": req.version,
                "commit_hash": req.commit_hash,
                "author": req.author,
                "status": req.status,
                "metadata": req.metadata,
            },
        )

    @staticmethod
    def normalize_otel_span(span: OTelSpan, service: str, environment: str) -> NormalizedEvent:
        sev = Severity.CRITICAL if span.status_code == "ERROR" else Severity.INFO
        msg = f"Span {span.name}: status {span.status_code}"
        if span.status_message:
            msg += f" - {span.status_message}"

        return NormalizedEvent(
            id=str(uuid.uuid4()),
            timestamp=span.start_time or datetime.now(timezone.utc),
            service=service.strip().lower(),
            environment=environment.strip().lower(),
            event_type=EventType.OTEL,
            severity=sev,
            message=msg,
            payload={
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "kind": span.kind,
                "attributes": span.attributes,
                "status_code": span.status_code,
                "status_message": span.status_message,
            },
            trace_id=span.trace_id,
        )

    @staticmethod
    def to_db_model(event: NormalizedEvent) -> Event:
        return Event(
            id=event.id or str(uuid.uuid4()),
            timestamp=event.timestamp,
            service=event.service,
            environment=event.environment,
            event_type=event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
            severity=event.severity.value if hasattr(event.severity, "value") else str(event.severity),
            message=event.message,
            payload=event.payload,
            trace_id=event.trace_id,
            correlation_id=event.correlation_id,
            is_anomaly=event.is_anomaly,
            anomaly_score=event.anomaly_score,
            incident_id=event.incident_id,
        )

