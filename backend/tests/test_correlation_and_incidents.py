import pytest
from backend.app.db.repositories import EventRepository, IncidentRepository
from backend.app.ingestion.schemas import (
    DeploymentIngestRequest,
    ErrorIngestRequest,
    MetricIngestRequest,
)
from backend.app.ingestion.deployment_ingestor import DeploymentIngestor
from backend.app.ingestion.error_ingestor import ErrorIngestor
from backend.app.ingestion.metric_ingestor import MetricIngestor
from backend.app.processing.event_processor import EventProcessor


@pytest.mark.asyncio
async def test_event_processing_and_incident_creation(test_db):
    processor = EventProcessor(test_db)
    incident_repo = IncidentRepository(test_db)

    # 1. Ingest deployment
    dep = DeploymentIngestRequest(
        service="payment-service",
        version="v2.4.1",
        commit_hash="a1b2c3d4e5f6",
    )
    ev_dep, inc_id_dep = await processor.process_event(DeploymentIngestor.process(dep))
    assert inc_id_dep is None  # A healthy deployment alone should not trigger an incident

    # 2. Ingest critical metric anomaly (DB pool utilization 99%)
    metric = MetricIngestRequest(
        service="payment-service",
        metric_name="db_pool_utilization",
        value=99.0,
        unit="percent",
    )
    ev_met, inc_id_met = await processor.process_event(MetricIngestor.process(metric))
    assert inc_id_met is not None  # Should trigger an incident!
    assert inc_id_met.startswith("INC-")

    # Verify incident exists in DB
    inc = await incident_repo.get_by_id(inc_id_met)
    assert inc is not None
    assert inc.service == "payment-service"
    assert inc.status == "triggered"
    assert "payment" in inc.title.lower()
    assert "db_pool_utilization" in inc.description

    # 3. Ingest subsequent error - should correlate to the same existing incident
    err = ErrorIngestRequest(
        service="payment-service",
        error_class="DatabaseConnectionTimeout",
        error_message="Could not acquire connection from pool",
        http_status=500,
    )
    ev_err, inc_id_err = await processor.process_event(ErrorIngestor.process(err))
    assert inc_id_err == inc_id_met  # Correlated!
