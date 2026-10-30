from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.repositories import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuditRepository(db)

    async def get_audit_trail(self, incident_id: str) -> List[Dict[str, Any]]:
        logs = await self.repo.list_by_incident(incident_id)
        return [
            {
                "id": log.id,
                "incident_id": log.incident_id,
                "actor": log.actor,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ]

