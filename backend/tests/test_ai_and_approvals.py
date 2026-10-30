import pytest
from backend.app.ai.agent import IncidentInvestigationAgent
from backend.app.db.repositories import ApprovalRepository, IncidentRepository
from backend.app.ingestion.schemas import (
    DeploymentIngestRequest,
    ErrorIngestRequest,
    MetricIngestRequest,
)
from backend.app.ingestion.deployment_ingestor import DeploymentIngestor
from backend.app.ingestion.error_ingestor import ErrorIngestor
from backend.app.ingestion.metric_ingestor import MetricIngestor
from backend.app.processing.event_processor import EventProcessor
from backend.app.remediation.approval import ApprovalWorkflowService


@pytest.mark.asyncio
async def test_ai_investigation_and_approval_workflow(test_db):
    processor = EventProcessor(test_db)
    incident_repo = IncidentRepository(test_db)
    approval_repo = ApprovalRepository(test_db)

    # 1. Setup outage events
    # Deployment
    dep = DeploymentIngestRequest(
        service="payment-service",
        version="v2.4.1",
        commit_hash="f00ba1234567",
        status="completed",
    )
    await processor.process_event(DeploymentIngestor.process(dep))

    # Metric anomaly
    met = MetricIngestRequest(
        service="payment-service",
        metric_name="db_pool_utilization",
        value=98.5,
        unit="percent",
    )
    _, inc_id = await processor.process_event(MetricIngestor.process(met))
    assert inc_id is not None

    # Error
    err = ErrorIngestRequest(
        service="payment-service",
        error_class="DatabaseConnectionTimeout",
        error_message="HikariPool-1 - Connection is not available",
        http_status=500,
    )
    await processor.process_event(ErrorIngestor.process(err))

    # 2. Run AI Investigation Agent
    agent = IncidentInvestigationAgent(test_db)
    report_res = await agent.investigate_incident(inc_id)

    assert report_res["incident_id"] == inc_id
    assert report_res["status"] == "identified"
    assert len(report_res["hypotheses"]) > 0
    top_hyp = report_res["hypotheses"][0]
    assert "Database Connection Pool" in top_hyp["title"]
    assert top_hyp["confidence_score"] >= 0.70
    assert len(top_hyp["supporting_evidence_ids"]) > 0
    assert len(report_res["supporting_evidence"]) > 0

    # 3. Check Approval Requests generated
    pending_approvals = await approval_repo.list_by_incident(inc_id)
    assert len(pending_approvals) > 0
    appr = pending_approvals[0]
    assert appr.status == "pending"

    # 4. Human Approval Workflow: Approve & Execute
    workflow = ApprovalWorkflowService(test_db)
    exec_result = await workflow.approve_and_execute(approval_id=appr.id, approved_by="sre_lead")

    assert exec_result["status"] == "executed"
    assert exec_result["approved_by"] == "sre_lead"
    assert exec_result["execution_result"]["status"] == "success"

    # 5. Verify incident is now resolved
    updated_incident = await incident_repo.get_by_id(inc_id)
    assert updated_incident.status == "resolved"
    assert updated_incident.resolved_at is not None

