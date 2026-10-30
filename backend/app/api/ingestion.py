from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.ingestion.schemas import (
    BatchIngestRequest,
    DeploymentIngestRequest,
    ErrorIngestRequest,
    LogIngestRequest,
    MetricIngestRequest,
    OTelIngestRequest,
)
from backend.app.ingestion.deployment_ingestor import DeploymentIngestor
from backend.app.ingestion.error_ingestor import ErrorIngestor
from backend.app.ingestion.log_ingestor import LogIngestor
from backend.app.ingestion.metric_ingestor import MetricIngestor
from backend.app.ingestion.otel_ingestor import OTelIngestor
from backend.app.processing.event_processor import EventProcessor

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def ingest_log(req: LogIngestRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    norm_event = LogIngestor.process(req)
    processor = EventProcessor(db)
    saved_event, incident_id = await processor.process_event(norm_event)
    return {
        "status": "accepted",
        "event_id": saved_event.id,
        "is_anomaly": saved_event.is_anomaly,
        "incident_id": incident_id,
    }


@router.post("/error", status_code=status.HTTP_201_CREATED)
async def ingest_error(req: ErrorIngestRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    norm_event = ErrorIngestor.process(req)
    processor = EventProcessor(db)
    saved_event, incident_id = await processor.process_event(norm_event)
    return {
        "status": "accepted",
        "event_id": saved_event.id,
        "is_anomaly": saved_event.is_anomaly,
        "incident_id": incident_id,
    }


@router.post("/metric", status_code=status.HTTP_201_CREATED)
async def ingest_metric(req: MetricIngestRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    norm_event = MetricIngestor.process(req)
    processor = EventProcessor(db)
    saved_event, incident_id = await processor.process_event(norm_event)
    return {
        "status": "accepted",
        "event_id": saved_event.id,
        "is_anomaly": saved_event.is_anomaly,
        "incident_id": incident_id,
    }


@router.post("/deployment", status_code=status.HTTP_201_CREATED)
async def ingest_deployment(req: DeploymentIngestRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    norm_event = DeploymentIngestor.process(req)
    processor = EventProcessor(db)
    saved_event, incident_id = await processor.process_event(norm_event)
    return {
        "status": "accepted",
        "event_id": saved_event.id,
        "is_anomaly": saved_event.is_anomaly,
        "incident_id": incident_id,
    }


@router.post("/otel", status_code=status.HTTP_201_CREATED)
async def ingest_otel(req: OTelIngestRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    norm_events = OTelIngestor.process(req)
    processor = EventProcessor(db)
    results = []
    triggered_incident_id = None
    for ev in norm_events:
        saved_ev, inc_id = await processor.process_event(ev)
        if inc_id:
            triggered_incident_id = inc_id
        results.append(saved_ev.id)
    return {
        "status": "accepted",
        "processed_spans": len(results),
        "incident_id": triggered_incident_id,
    }


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def ingest_batch(req: BatchIngestRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    processor = EventProcessor(db)
    processed_count = 0
    incidents_triggered = []
    
    for raw in req.events:
        event_type = raw.get("event_type", "log")
        if event_type == "log":
            norm = LogIngestor.process(LogIngestRequest(**raw))
        elif event_type == "error":
            norm = ErrorIngestor.process(ErrorIngestRequest(**raw))
        elif event_type == "metric":
            norm = MetricIngestor.process(MetricIngestRequest(**raw))
        elif event_type == "deployment":
            norm = DeploymentIngestor.process(DeploymentIngestRequest(**raw))
        else:
            continue
            
        saved, inc_id = await processor.process_event(norm)
        processed_count += 1
        if inc_id and inc_id not in incidents_triggered:
            incidents_triggered.append(inc_id)

    return {
        "status": "accepted",
        "processed_count": processed_count,
        "incidents_affected": incidents_triggered,
    }

