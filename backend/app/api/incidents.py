from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.audit.audit_service import AuditService
from backend.app.db.repositories import EventRepository, IncidentRepository
from backend.app.db.session import get_db
from backend.app.incidents.incident_manager import IncidentManager
from backend.app.incidents.timeline import IncidentTimelineService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class UpdateIncidentRequest(BaseModel):
    status: Optional[str] = None
    confirmed_root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None
    actor: str = "engineer"


@router.get("", response_model=List[Dict[str, Any]])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (triggered, investigating, identified, resolved, closed)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    repo = IncidentRepository(db)
    incidents = await repo.list_incidents(
        status=status, severity=severity, service=service, limit=limit
    )
    return [
        {
            "id": inc.id,
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity,
            "status": inc.status,
            "service": inc.service,
            "environment": inc.environment,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
            "confirmed_root_cause": inc.confirmed_root_cause,
        }
        for inc in incidents
    ]


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "service": incident.service,
        "environment": incident.environment,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "confirmed_root_cause": incident.confirmed_root_cause,
        "resolution_notes": incident.resolution_notes,
    }


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str, req: UpdateIncidentRequest, db: AsyncSession = Depends(get_db)
):
    manager = IncidentManager(db)
    incident = await manager.update_status(
        incident_id=incident_id,
        new_status=req.status or "investigating",
        actor=req.actor,
        notes=req.resolution_notes,
        confirmed_root_cause=req.confirmed_root_cause,
    )
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return {
        "id": incident.id,
        "status": incident.status,
        "confirmed_root_cause": incident.confirmed_root_cause,
        "resolution_notes": incident.resolution_notes,
    }


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str, db: AsyncSession = Depends(get_db)):
    timeline_service = IncidentTimelineService(db)
    return await timeline_service.get_timeline(incident_id)


@router.get("/{incident_id}/events")
async def get_incident_events(incident_id: str, db: AsyncSession = Depends(get_db)):
    repo = EventRepository(db)
    events = await repo.list_by_incident_id(incident_id)
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "service": e.service,
            "event_type": e.event_type,
            "severity": e.severity,
            "message": e.message,
            "is_anomaly": e.is_anomaly,
            "anomaly_score": e.anomaly_score,
            "payload": e.payload,
        }
        for e in events
    ]


@router.get("/{incident_id}/audit")
async def get_incident_audit_trail(incident_id: str, db: AsyncSession = Depends(get_db)):
    audit_service = AuditService(db)
    return await audit_service.get_audit_trail(incident_id)

