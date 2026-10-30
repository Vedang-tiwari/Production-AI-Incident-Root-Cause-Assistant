from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.agent import IncidentInvestigationAgent
from backend.app.db.session import get_db
from backend.app.ingestion.schemas import (
    DeploymentIngestRequest,
    ErrorIngestRequest,
    LogIngestRequest,
    MetricIngestRequest,
)
from backend.app.ingestion.deployment_ingestor import DeploymentIngestor
from backend.app.ingestion.error_ingestor import ErrorIngestor
from backend.app.ingestion.log_ingestor import LogIngestor
from backend.app.ingestion.metric_ingestor import MetricIngestor
from backend.app.processing.event_processor import EventProcessor

router = APIRouter(prefix="/simulator", tags=["Outage Simulator"])


class ScenarioTriggerRequest(BaseModel):
    scenario: str = "payment-db-pool-exhaustion"  # "payment-db-pool-exhaustion", "order-memory-leak", "checkout-gateway-timeout"
    auto_investigate: bool = True


@router.post("/trigger-scenario", status_code=status.HTTP_201_CREATED)
async def trigger_scenario(
    req: ScenarioTriggerRequest, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    processor = EventProcessor(db)
    now = datetime.now(timezone.utc)
    scenario = req.scenario.lower().strip()

    events_created = []
    target_incident_id = None

    if scenario == "payment-db-pool-exhaustion":
        # 1. Preceding deployment (10 mins ago)
        dep_req = DeploymentIngestRequest(
            service="payment-service",
            version="v2.4.1",
            commit_hash="a9f2bc4810e7",
            author="alex.dev@corp.internal",
            status="completed",
            timestamp=now - timedelta(minutes=10),
            metadata={"git_branch": "release/v2.4", "changelog": "Added audit connection wrapper"},
        )
        e1, _ = await processor.process_event(DeploymentIngestor.process(dep_req))
        events_created.append(e1.id)

        # 2. Metric: DB Pool utilization reaches 98% (5 mins ago)
        met_req = MetricIngestRequest(
            service="payment-service",
            metric_name="db_pool_utilization",
            value=98.5,
            unit="percent",
            timestamp=now - timedelta(minutes=5),
        )
        e2, inc_id2 = await processor.process_event(MetricIngestor.process(met_req))
        events_created.append(e2.id)
        if inc_id2:
            target_incident_id = inc_id2

        # 3. Metric: Latency spike to 2850ms
        met_latency = MetricIngestRequest(
            service="payment-service",
            metric_name="request_latency_ms",
            value=2850.0,
            unit="ms",
            timestamp=now - timedelta(minutes=3),
        )
        e3, inc_id3 = await processor.process_event(MetricIngestor.process(met_latency))
        events_created.append(e3.id)
        if inc_id3:
            target_incident_id = inc_id3

        # 4. Application Log: Pool exhausted timeout
        log_req = LogIngestRequest(
            service="payment-service",
            level="error",
            message="HikariPool-1 - Connection is not available, request timed out after 30000ms",
            timestamp=now - timedelta(minutes=2),
            metadata={"pool_max": 10, "pool_active": 10, "pending_threads": 42},
        )
        e4, inc_id4 = await processor.process_event(LogIngestor.process(log_req))
        events_created.append(e4.id)
        if inc_id4:
            target_incident_id = inc_id4

        # 5. Critical Error: HTTP 500
        err_req = ErrorIngestRequest(
            service="payment-service",
            error_class="DatabaseConnectionTimeout",
            error_message="Could not acquire database connection from pool within 30000ms",
            http_status=500,
            timestamp=now,
            stack_trace=(
                "Traceback (most recent call last):\n"
                "  File 'app/services/payment.py', line 84, in process_charge\n"
                "    with db_pool.get_connection() as conn:\n"
                "  File 'lib/db/pool.py', line 112, in get_connection\n"
                "    raise PoolExhaustedError('HikariPool-1 connection timeout')"
            ),
        )
        e5, inc_id5 = await processor.process_event(ErrorIngestor.process(err_req))
        events_created.append(e5.id)
        if inc_id5:
            target_incident_id = inc_id5

    elif scenario == "order-memory-leak":
        # 1. Preceding deployment
        dep_req = DeploymentIngestRequest(
            service="order-service",
            version="v2.3.1",
            commit_hash="c3d7890a1b2",
            author="sara.eng@corp.internal",
            status="completed",
            timestamp=now - timedelta(minutes=15),
            metadata={"git_branch": "feature/order-cache"},
        )
        e1, _ = await processor.process_event(DeploymentIngestor.process(dep_req))
        events_created.append(e1.id)

        # 2. Memory utilization surges to 96.5%
        met_req = MetricIngestRequest(
            service="order-service",
            metric_name="memory_utilization_percent",
            value=96.5,
            unit="percent",
            timestamp=now - timedelta(minutes=4),
        )
        e2, inc_id2 = await processor.process_event(MetricIngestor.process(met_req))
        events_created.append(e2.id)
        if inc_id2:
            target_incident_id = inc_id2

        # 3. Critical Error: OOMKilled
        err_req = ErrorIngestRequest(
            service="order-service",
            error_class="OutOfMemoryError",
            error_message="Java heap space exhausted. Pod terminated with exit code 137 (OOMKilled).",
            http_status=500,
            timestamp=now,
        )
        e3, inc_id3 = await processor.process_event(ErrorIngestor.process(err_req))
        events_created.append(e3.id)
        if inc_id3:
            target_incident_id = inc_id3

    elif scenario == "checkout-gateway-timeout":
        # 1. Latency spike
        met_req = MetricIngestRequest(
            service="checkout-service",
            metric_name="gateway_latency_ms",
            value=4500.0,
            unit="ms",
            timestamp=now - timedelta(minutes=5),
        )
        e1, inc_id1 = await processor.process_event(MetricIngestor.process(met_req))
        events_created.append(e1.id)
        if inc_id1:
            target_incident_id = inc_id1

        # 2. HTTP 504 Error
        err_req = ErrorIngestRequest(
            service="checkout-service",
            error_class="GatewayTimeoutError",
            error_message="HTTP 504: Downstream payment provider response timed out after 4500ms",
            http_status=504,
            timestamp=now,
        )
        e2, inc_id2 = await processor.process_event(ErrorIngestor.process(err_req))
        events_created.append(e2.id)
        if inc_id2:
            target_incident_id = inc_id2

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{scenario}'. Supported scenarios: 'payment-db-pool-exhaustion', 'order-memory-leak', 'checkout-gateway-timeout'",
        )

    investigation_result = None
    if req.auto_investigate and target_incident_id:
        agent = IncidentInvestigationAgent(db)
        investigation_result = await agent.investigate_incident(target_incident_id)

    return {
        "scenario": scenario,
        "events_generated": len(events_created),
        "incident_id": target_incident_id,
        "investigation_triggered": req.auto_investigate and target_incident_id is not None,
        "investigation": investigation_result,
    }

