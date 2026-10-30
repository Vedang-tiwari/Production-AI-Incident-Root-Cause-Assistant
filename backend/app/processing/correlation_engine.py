from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models import Event, Incident
from backend.app.db.repositories import EventRepository, IncidentRepository
from backend.app.ingestion.schemas import NormalizedEvent, Severity


class CorrelationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_repo = EventRepository(db)
        self.incident_repo = IncidentRepository(db)

    async def correlate_event(self, event: NormalizedEvent) -> Tuple[Optional[str], bool]:
        """
        Correlates an incoming event with existing incidents or determines if a new incident is needed.
        Returns: (incident_id, is_new_incident_trigger)
        """
        # Look for existing active incident for this service within the correlation window
        window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.CORRELATION_WINDOW_MINUTES)
        active_incident = await self.incident_repo.find_active_incident_for_service(
            service=event.service, window_start=window_start
        )

        # 1. If an active incident already exists for this service, associate it!
        if active_incident:
            logger.info(
                f"Correlated event {event.event_type} on {event.service} to active incident {active_incident.id}"
            )
            return active_incident.id, False

        # 2. Check if this event qualifies as a new incident trigger
        should_trigger = False
        if event.is_anomaly and event.anomaly_score >= 0.70:
            should_trigger = True
        elif event.severity == Severity.CRITICAL:
            should_trigger = True

        # If it's a candidate, check recent events for this service to detect event clustering
        if not should_trigger and event.is_anomaly:
            recent_events = await self.event_repo.list_by_service_and_window(
                service=event.service,
                start_time=window_start,
                end_time=datetime.now(timezone.utc),
            )
            # If 3 or more errors or anomalies occurred recently, escalate into an incident
            anomalous_recent = [e for e in recent_events if e.is_anomaly or e.severity in ["high", "critical"]]
            if len(anomalous_recent) >= 2:
                should_trigger = True
                logger.info(
                    f"Cluster of {len(anomalous_recent) + 1} anomalies detected for {event.service}. Triggering incident."
                )

        return None, should_trigger

    async def find_related_deployments(self, service: str, incident_time: datetime) -> List[Event]:
        """Find deployments for the service in the 60 minutes preceding the incident."""
        start_time = incident_time - timedelta(minutes=60)
        events = await self.event_repo.list_by_service_and_window(
            service=service,
            start_time=start_time,
            end_time=incident_time + timedelta(minutes=5),
        )
        return [e for e in events if e.event_type == "deployment"]

    async def find_related_anomalies(self, service: str, incident_time: datetime) -> List[Event]:
        """Find anomalous events for the service in the correlation window."""
        start_time = incident_time - timedelta(minutes=settings.CORRELATION_WINDOW_MINUTES)
        events = await self.event_repo.list_by_service_and_window(
            service=service,
            start_time=start_time,
            end_time=incident_time + timedelta(minutes=settings.CORRELATION_WINDOW_MINUTES),
        )
        return [e for e in events if e.is_anomaly or e.severity in ["high", "critical"]]

