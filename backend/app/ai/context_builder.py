from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.db.models import Incident
from backend.app.db.repositories import EventRepository, TimelineRepository
from backend.app.rag.retriever import KnowledgeRetriever


class IncidentContextBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_repo = EventRepository(db)
        self.timeline_repo = TimelineRepository(db)
        self.retriever = KnowledgeRetriever(db)

    async def build_context(self, incident: Incident) -> Dict[str, Any]:
        """
        Builds a comprehensive investigation context for the AI agent.
        Collects logs, errors, metrics, deployments, timeline, historical incidents, and runbooks.
        """
        incident_time = incident.created_at or datetime.now(timezone.utc)
        window_start = incident_time - timedelta(minutes=settings.CORRELATION_WINDOW_MINUTES * 2)
        window_end = incident_time + timedelta(minutes=settings.CORRELATION_WINDOW_MINUTES)

        # 1. Fetch related events for the service in the window
        all_events = await self.event_repo.list_by_service_and_window(
            service=incident.service,
            start_time=window_start,
            end_time=window_end,
            limit=100,
        )

        logs = [e for e in all_events if e.event_type == "log"]
        errors = [e for e in all_events if e.event_type in ["error", "otel"]]
        metrics = [e for e in all_events if e.event_type == "metric"]
        deployments = [e for e in all_events if e.event_type == "deployment"]
        anomalies = [e for e in all_events if e.is_anomaly]

        # 2. Fetch existing timeline
        timeline_items = await self.timeline_repo.list_by_incident(incident.id)

        # 3. Retrieve relevant RAG knowledge
        search_query = f"{incident.service} {incident.title} {incident.description}"
        if errors:
            search_query += f" {' '.join(e.message for e in errors[:3])}"

        runbooks = await self.retriever.retrieve_runbooks(
            query=search_query, service=incident.service, top_k=2
        )
        historical_incidents = await self.retriever.retrieve_historical_incidents(
            query=search_query, service=incident.service, top_k=2
        )

        return {
            "incident": {
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "service": incident.service,
                "severity": incident.severity,
                "status": incident.status,
                "created_at": incident_time.isoformat(),
            },
            "events_summary": {
                "total_events": len(all_events),
                "error_count": len(errors),
                "anomaly_count": len(anomalies),
                "deployment_count": len(deployments),
            },
            "recent_deployments": [
                {
                    "id": d.id,
                    "timestamp": d.timestamp.isoformat(),
                    "message": d.message,
                    "version": d.payload.get("version"),
                    "commit_hash": d.payload.get("commit_hash"),
                    "status": d.payload.get("status"),
                }
                for d in deployments
            ],
            "anomalies": [
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat(),
                    "type": a.event_type,
                    "message": a.message,
                    "score": a.anomaly_score,
                }
                for a in anomalies
            ],
            "sample_errors": [
                {
                    "id": er.id,
                    "timestamp": er.timestamp.isoformat(),
                    "message": er.message,
                    "payload": er.payload,
                }
                for er in errors[:10]
            ],
            "metrics": [
                {
                    "id": m.id,
                    "timestamp": m.timestamp.isoformat(),
                    "metric_name": m.payload.get("metric_name"),
                    "value": m.payload.get("value"),
                    "unit": m.payload.get("unit"),
                }
                for m in metrics[:10]
            ],
            "timeline": [
                {
                    "id": t.id,
                    "timestamp": t.timestamp.isoformat(),
                    "type": t.event_type,
                    "title": t.title,
                    "description": t.description,
                }
                for t in timeline_items
            ],
            "retrieved_runbooks": runbooks,
            "similar_historical_incidents": historical_incidents,
        }

