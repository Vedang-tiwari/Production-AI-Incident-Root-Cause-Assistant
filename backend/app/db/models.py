import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    service = Column(String(100), nullable=False, index=True)
    environment = Column(String(50), default="production", nullable=False)
    event_type = Column(String(50), nullable=False, index=True)  # log, error, metric, deployment, otel
    severity = Column(String(20), default="info", nullable=False)  # info, low, medium, high, critical
    message = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    trace_id = Column(String(100), nullable=True, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    is_anomaly = Column(Boolean, default=False, nullable=False)
    anomaly_score = Column(Float, default=0.0, nullable=False)

    incident_id = Column(String(50), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    incident = relationship("Incident", back_populates="events")

    __table_args__ = (
        Index("idx_events_service_time", "service", "timestamp"),
        Index("idx_events_type_severity", "event_type", "severity"),
    )


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(50), primary_key=True)  # e.g. INC-2026-001 or UUID
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="medium", nullable=False, index=True)  # low, medium, high, critical
    status = Column(String(30), default="triggered", nullable=False, index=True)  # triggered, investigating, identified, resolved, closed
    service = Column(String(100), nullable=False, index=True)
    environment = Column(String(50), default="production", nullable=False)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    confirmed_root_cause = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    events = relationship("Event", back_populates="incident", lazy="selectin")
    timeline_events = relationship("TimelineEvent", back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    investigation_reports = relationship("InvestigationReport", back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    approval_requests = relationship("ApprovalRequest", back_populates="incident", cascade="all, delete-orphan", lazy="selectin")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(50), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    event_type = Column(String(50), nullable=False)  # deployment, anomaly, error_spike, investigation, recommendation, approval, resolved
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source_ref = Column(String(100), nullable=True)  # event_id or commit hash or tool ref
    metadata_json = Column(JSON, default=dict)

    incident = relationship("Incident", back_populates="timeline_events")


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(50), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    hypotheses = Column(JSON, default=list, nullable=False)  # [{title, likelihood, confidence_score, rationale, supporting_evidence_ids}]
    supporting_evidence = Column(JSON, default=list, nullable=False)  # [{id, type, source, summary, timestamp}]
    recommendations = Column(JSON, default=list, nullable=False)  # [{action, risk_level, description, requires_approval, command}]
    confidence_score = Column(Float, default=0.0, nullable=False)
    uncertainty_factors = Column(JSON, default=list)  # ["string"]
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    incident = relationship("Incident", back_populates="investigation_reports")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(50), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # rollback, restart, scale_pool, config_fix, create_jira
    description = Column(Text, nullable=False)
    risk_level = Column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, approved, rejected, executed, failed
    requested_by = Column(String(100), default="ai_investigation_agent", nullable=False)
    approved_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    execution_result = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    incident = relationship("Incident", back_populates="approval_requests")


class HistoricalIncident(Base):
    __tablename__ = "historical_incidents"

    id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    service = Column(String(100), nullable=False, index=True)
    root_cause = Column(Text, nullable=False)
    resolution = Column(Text, nullable=False)
    error_signatures = Column(JSON, default=list)
    resolved_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    embedding_vector = Column(JSON, nullable=True)


class Runbook(Base):
    __tablename__ = "runbooks"

    id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    service = Column(String(100), nullable=False, index=True)
    category = Column(String(100), default="troubleshooting", nullable=False)
    tags = Column(JSON, default=list)
    content_markdown = Column(Text, nullable=False)
    embedding_vector = Column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(50), nullable=True, index=True)
    actor = Column(String(100), nullable=False)  # system, ai_agent, user:<name>
    action = Column(String(100), nullable=False, index=True)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

