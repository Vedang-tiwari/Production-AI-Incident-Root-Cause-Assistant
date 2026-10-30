from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import Event


class MetricsAnalysisTool:
    name = "metrics_analysis"
    description = "Analyzes service metrics, calculates average/peak values, and surfaces threshold breaches."

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, service: str, metric_name: Optional[str] = None) -> Dict[str, Any]:
        stmt = (
            select(Event)
            .where(
                Event.service == service,
                Event.event_type == "metric",
            )
            .order_by(Event.timestamp.desc())
            .limit(50)
        )
        result = await self.db.execute(stmt)
        metric_events = list(result.scalars().all())

        if metric_name:
            metric_events = [
                m for m in metric_events if m.payload.get("metric_name", "").lower() == metric_name.lower()
            ]

        # Group and aggregate
        grouped: Dict[str, List[float]] = {}
        for m in metric_events:
            name = m.payload.get("metric_name", "unknown")
            val = float(m.payload.get("value", 0.0))
            grouped.setdefault(name, []).append(val)

        summary = {}
        for name, values in grouped.items():
            avg_val = sum(values) / len(values) if values else 0.0
            max_val = max(values) if values else 0.0
            latest_val = values[0] if values else 0.0
            summary[name] = {
                "latest": latest_val,
                "average": round(avg_val, 2),
                "peak": max_val,
                "samples_count": len(values),
                "is_anomalous": any(m.is_anomaly for m in metric_events if m.payload.get("metric_name") == name),
            }

        return {
            "service": service,
            "metrics_analyzed": summary,
        }

