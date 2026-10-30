from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.logging import logger
from backend.app.db.models import Event, Incident
from backend.app.db.repositories import EventRepository
from backend.app.incidents.incident_manager import IncidentManager
from backend.app.ingestion.schemas import NormalizedEvent
from backend.app.processing.anomaly_detector import AnomalyDetector
from backend.app.processing.correlation_engine import CorrelationEngine
from backend.app.processing.normalizer import EventNormalizer


class EventProcessor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_repo = EventRepository(db)
        self.anomaly_detector = AnomalyDetector()
        self.correlation_engine = CorrelationEngine(db)
        self.incident_manager = IncidentManager(db)

    async def process_event(self, event: NormalizedEvent) -> Tuple[Event, Optional[str]]:
        """
        Processes an incoming normalized event:
        1. Evaluates for anomalies.
        2. Correlates with existing active incidents or triggers a new incident.
        3. Persists event to the database.
        Returns: (saved_db_event, incident_id)
        """
        # Step 1: Anomaly Detection
        is_anomaly, score, reason = self.anomaly_detector.evaluate(event)
        if is_anomaly:
            logger.warning(
                f"[Anomaly Detected] {event.service}: score={score:.2f} reason={reason}"
            )

        # Step 2: Correlation Engine
        existing_incident_id, should_trigger_new = await self.correlation_engine.correlate_event(event)

        created_incident: Optional[Incident] = None
        target_incident_id = existing_incident_id

        if should_trigger_new and not existing_incident_id:
            # Find related recent deployments
            related_deployments = await self.correlation_engine.find_related_deployments(
                service=event.service, incident_time=event.timestamp
            )
            created_incident = await self.incident_manager.create_incident_from_event(
                trigger_event=event, related_events=related_deployments
            )
            target_incident_id = created_incident.id

        event.incident_id = target_incident_id

        # Step 3: Persist Event to DB
        db_model = EventNormalizer.to_db_model(event)
        saved_event = await self.event_repo.create(db_model)

        return saved_event, target_incident_id

