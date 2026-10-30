from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import Event


class DeploymentAnalysisTool:
    name = "deployment_analysis"
    description = "Examines recent deployments for a service and identifies git commits, release tags, and deployment statuses."

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, service: str, limit: int = 5) -> List[Dict[str, Any]]:
        stmt = (
            select(Event)
            .where(
                Event.service == service,
                Event.event_type == "deployment",
            )
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        deploy_events = list(result.scalars().all())

        return [
            {
                "id": d.id,
                "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                "version": d.payload.get("version"),
                "commit_hash": d.payload.get("commit_hash"),
                "author": d.payload.get("author"),
                "status": d.payload.get("status"),
                "metadata": d.payload.get("metadata", {}),
            }
            for d in deploy_events
        ]

