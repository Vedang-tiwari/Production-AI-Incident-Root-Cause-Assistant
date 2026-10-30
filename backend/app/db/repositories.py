from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import (
    ApprovalRequest,
    AuditLog,
    Event,
    HistoricalIncident,
    Incident,
    InvestigationReport,
    Runbook,
    TimelineEvent,
)


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: Event) -> Event:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def create_many(self, events: List[Event]) -> List[Event]:
        self.db.add_all(events)
        await self.db.commit()
        for ev in events:
            await self.db.refresh(ev)
        return events

    async def get_by_id(self, event_id: str) -> Optional[Event]:
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        return result.scalars().first()

    async def list_by_service_and_window(
        self, service: str, start_time: datetime, end_time: datetime, limit: int = 100
    ) -> List[Event]:
        stmt = (
            select(Event)
            .where(
                Event.service == service,
                Event.timestamp >= start_time,
                Event.timestamp <= end_time,
            )
            .order_by(Event.timestamp.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_incident_id(self, incident_id: str, limit: int = 200) -> List[Event]:
        stmt = (
            select(Event)
            .where(Event.incident_id == incident_id)
            .order_by(Event.timestamp.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50, service: Optional[str] = None) -> List[Event]:
        stmt = select(Event).order_by(desc(Event.timestamp)).limit(limit)
        if service:
            stmt = stmt.where(Event.service == service)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class IncidentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, incident: Incident) -> Incident:
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def get_by_id(self, incident_id: str) -> Optional[Incident]:
        stmt = select(Incident).where(Incident.id == incident_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 50,
    ) -> List[Incident]:
        stmt = select(Incident).order_by(desc(Incident.created_at)).limit(limit)
        if status:
            stmt = stmt.where(Incident.status == status)
        if severity:
            stmt = stmt.where(Incident.severity == severity)
        if service:
            stmt = stmt.where(Incident.service == service)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_active_incident_for_service(
        self, service: str, window_start: Optional[datetime] = None
    ) -> Optional[Incident]:
        """Find an active (non-resolved, non-closed) incident for the given service."""
        stmt = (
            select(Incident)
            .where(
                Incident.service == service,
                Incident.status.in_(["triggered", "investigating", "identified"]),
            )
            .order_by(desc(Incident.created_at))
        )
        if window_start:
            stmt = stmt.where(Incident.created_at >= window_start)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_status(
        self,
        incident_id: str,
        status: str,
        confirmed_root_cause: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[Incident]:
        incident = await self.get_by_id(incident_id)
        if not incident:
            return None
        incident.status = status
        incident.updated_at = datetime.now(timezone.utc)
        if confirmed_root_cause:
            incident.confirmed_root_cause = confirmed_root_cause
        if resolution_notes:
            incident.resolution_notes = resolution_notes
        if status in ["resolved", "closed"] and not incident.resolved_at:
            incident.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident


class TimelineRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_entry(self, entry: TimelineEvent) -> TimelineEvent:
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_by_incident(self, incident_id: str) -> List[TimelineEvent]:
        stmt = (
            select(TimelineEvent)
            .where(TimelineEvent.incident_id == incident_id)
            .order_by(TimelineEvent.timestamp.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class InvestigationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, report: InvestigationReport) -> InvestigationReport:
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_latest_by_incident(self, incident_id: str) -> Optional[InvestigationReport]:
        stmt = (
            select(InvestigationReport)
            .where(InvestigationReport.incident_id == incident_id)
            .order_by(desc(InvestigationReport.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()


class ApprovalRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_incident(self, incident_id: str) -> List[ApprovalRequest]:
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.incident_id == incident_id)
            .order_by(desc(ApprovalRequest.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_pending(self) -> List[ApprovalRequest]:
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == "pending")
            .order_by(desc(ApprovalRequest.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_decision(
        self,
        approval_id: str,
        status: str,
        approved_by: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[ApprovalRequest]:
        approval = await self.get_by_id(approval_id)
        if not approval:
            return None
        approval.status = status
        approval.approved_by = approved_by
        approval.rejection_reason = rejection_reason
        if execution_result:
            approval.execution_result = execution_result
        approval.responded_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval


class KnowledgeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_runbook(self, runbook: Runbook) -> Runbook:
        # Merge if exists
        existing = await self.db.get(Runbook, runbook.id)
        if existing:
            existing.title = runbook.title
            existing.service = runbook.service
            existing.category = runbook.category
            existing.tags = runbook.tags
            existing.content_markdown = runbook.content_markdown
            existing.embedding_vector = runbook.embedding_vector
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        self.db.add(runbook)
        await self.db.commit()
        await self.db.refresh(runbook)
        return runbook

    async def get_all_runbooks(self, service: Optional[str] = None) -> List[Runbook]:
        stmt = select(Runbook)
        if service:
            stmt = stmt.where(Runbook.service == service)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_historical_incident(self, incident: HistoricalIncident) -> HistoricalIncident:
        existing = await self.db.get(HistoricalIncident, incident.id)
        if existing:
            existing.title = incident.title
            existing.service = incident.service
            existing.root_cause = incident.root_cause
            existing.resolution = incident.resolution
            existing.error_signatures = incident.error_signatures
            existing.resolved_at = incident.resolved_at
            existing.embedding_vector = incident.embedding_vector
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def get_all_historical_incidents(self, service: Optional[str] = None) -> List[HistoricalIncident]:
        stmt = select(HistoricalIncident)
        if service:
            stmt = stmt.where(HistoricalIncident.service == service)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self, actor: str, action: str, details: Dict[str, Any], incident_id: Optional[str] = None
    ) -> AuditLog:
        entry = AuditLog(
            actor=actor,
            action=action,
            details=details,
            incident_id=incident_id,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_by_incident(self, incident_id: str) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.incident_id == incident_id)
            .order_by(desc(AuditLog.timestamp))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

