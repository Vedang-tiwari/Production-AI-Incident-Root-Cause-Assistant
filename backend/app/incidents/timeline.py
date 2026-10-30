from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import TimelineEvent
from backend.app.db.repositories import TimelineRepository


class IncidentTimelineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeline_repo = TimelineRepository(db)

    async def get_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        events = await self.timeline_repo.list_by_incident(incident_id)
        return [
            {
                "id": ev.id,
                "incident_id": ev.incident_id,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "event_type": ev.event_type,
                "title": ev.title,
                "description": ev.description,
                "source_ref": ev.source_ref,
                "metadata": ev.metadata_json or {},
            }
            for ev in events
        ]

