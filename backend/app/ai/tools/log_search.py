from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import Event


class LogSearchTool:
    name = "log_search"
    description = "Searches application logs and errors matching service name, keyword queries, and timestamps."

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        service: str,
        query: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(Event)
            .where(
                Event.service == service,
                Event.event_type.in_(["log", "error", "otel"]),
            )
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
        if severity:
            stmt = stmt.where(Event.severity == severity)

        result = await self.db.execute(stmt)
        events = list(result.scalars().all())

        if query:
            q = query.lower()
            events = [e for e in events if q in e.message.lower() or q in str(e.payload).lower()]

        return [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "service": e.service,
                "severity": e.severity,
                "message": e.message,
                "payload": e.payload,
            }
            for e in events
        ]

