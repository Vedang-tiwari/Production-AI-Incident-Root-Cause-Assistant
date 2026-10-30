from datetime import datetime, timezone
import random
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.logging import logger
from backend.app.db.models import Event, Incident, TimelineEvent
from backend.app.db.repositories import (
    AuditRepository,
    EventRepository,
    IncidentRepository,
    TimelineRepository,
)
from backend.app.ingestion.schemas import NormalizedEvent, Severity


class IncidentManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.incident_repo = IncidentRepository(db)
        self.event_repo = EventRepository(db)
        self.timeline_repo = TimelineRepository(db)
        self.audit_repo = AuditRepository(db)

    @staticmethod
    def generate_incident_id() -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_suffix = random.randint(1000, 9999)
        return f"INC-{date_str}-{rand_suffix}"

    async def create_incident_from_event(
        self, trigger_event: NormalizedEvent, related_events: Optional[List[Event]] = None
    ) -> Incident:
        incident_id = self.generate_incident_id()
        
        # Determine title and severity
        severity = "critical" if trigger_event.severity == Severity.CRITICAL else "high"
        service_title = trigger_event.service.replace("-", " ").title()
        title = f"{service_title} Incident: {trigger_event.message[:80]}"
        description = (
            f"Automated incident triggered by {trigger_event.event_type.value if hasattr(trigger_event.event_type, 'value') else trigger_event.event_type} event: "
            f"{trigger_event.message}"
        )

        incident = Incident(
            id=incident_id,
            title=title,
            description=description,
            severity=severity,
            status="triggered",
            service=trigger_event.service,
            environment=trigger_event.environment,
            created_at=trigger_event.timestamp,
        )
        created_incident = await self.incident_repo.create(incident)

        # 1. Timeline: Incident Triggered
        trigger_timeline = TimelineEvent(
            incident_id=incident_id,
            timestamp=trigger_event.timestamp,
            event_type="incident_triggered",
            title="Incident Triggered",
            description=f"Anomaly detected in {trigger_event.service}: {trigger_event.message}",
            source_ref=trigger_event.id,
            metadata_json={
                "severity": severity,
                "anomaly_score": trigger_event.anomaly_score,
                "event_type": str(trigger_event.event_type),
            },
        )
        await self.timeline_repo.add_entry(trigger_timeline)

        # 2. Add related past events to timeline if available (e.g. recent deployment)
        if related_events:
            for ev in related_events:
                if ev.event_type == "deployment":
                    deploy_timeline = TimelineEvent(
                        incident_id=incident_id,
                        timestamp=ev.timestamp,
                        event_type="deployment",
                        title=f"Preceding Deployment: {ev.payload.get('version', 'unknown')}",
                        description=f"Commit {ev.payload.get('commit_hash', 'unknown')[:7]} deployed by {ev.payload.get('author', 'CI/CD')}",
                        source_ref=ev.id,
                        metadata_json=ev.payload,
                    )
                    await self.timeline_repo.add_entry(deploy_timeline)

        # 3. Log to audit trail
        await self.audit_repo.log_action(
            actor="incident_detection_engine",
            action="incident_created",
            details={
                "incident_id": incident_id,
                "service": trigger_event.service,
                "trigger_event_id": trigger_event.id,
                "severity": severity,
            },
            incident_id=incident_id,
        )

        logger.info(f"Created new incident {incident_id} for service {trigger_event.service}")
        return created_incident

    async def attach_event_to_incident(self, incident_id: str, event_id: str) -> None:
        db_event = await self.event_repo.get_by_id(event_id)
        if db_event:
            db_event.incident_id = incident_id
            await self.db.commit()

    async def update_status(
        self,
        incident_id: str,
        new_status: str,
        actor: str = "system",
        notes: Optional[str] = None,
        confirmed_root_cause: Optional[str] = None,
    ) -> Optional[Incident]:
        incident = await self.incident_repo.update_status(
            incident_id=incident_id,
            status=new_status,
            confirmed_root_cause=confirmed_root_cause,
            resolution_notes=notes,
        )
        if incident:
            # Timeline entry for status change
            timeline_entry = TimelineEvent(
                incident_id=incident_id,
                timestamp=datetime.now(timezone.utc),
                event_type="status_changed",
                title=f"Status changed to {new_status.upper()}",
                description=notes or f"Incident status transitioned to {new_status} by {actor}",
                metadata_json={"actor": actor, "new_status": new_status},
            )
            await self.timeline_repo.add_entry(timeline_entry)

            # Audit log
            await self.audit_repo.log_action(
                actor=actor,
                action="incident_status_updated",
                details={
                    "incident_id": incident_id,
                    "new_status": new_status,
                    "notes": notes,
                    "confirmed_root_cause": confirmed_root_cause,
                },
                incident_id=incident_id,
            )
        return incident

