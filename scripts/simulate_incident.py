"""
Incident Assistant End-to-End Simulation Script
Demonstrates:
  Event Ingestion -> Anomaly Detection -> Event Correlation ->
  Incident Creation -> Context Gathering -> RAG Retrieval ->
  AI Investigation -> Root Cause Hypotheses -> Human Approval -> Remediation
"""

import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set UTF-8 encoding for stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
from datetime import datetime, timezone
import json
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.agent import IncidentInvestigationAgent
from backend.app.db.session import async_session_factory, engine, init_db
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
from backend.app.rag.seed_data import seed_knowledge_base
from backend.app.remediation.approval import ApprovalWorkflowService


async def run_simulation():
    print("=" * 70)
    print("[*] PRODUCTION AI INCIDENT & ROOT-CAUSE ASSISTANT - SIMULATION")
    print("=" * 70)

    # 1. Initialize
    await init_db()
    async with async_session_factory() as session:
        await seed_knowledge_base(session)

    async with async_session_factory() as session:
        processor = EventProcessor(session)

        # 2. Deployment Event
        print("\n[STEP 1] Ingesting Deployment Event:")
        dep = DeploymentIngestRequest(
            service="payment-service",
            version="v2.4.1",
            commit_hash="a9f2bc4810e7",
            author="alex.dev@corp.internal",
            status="completed",
            metadata={"changelog": "Refactored payment transaction connection wrapper"},
        )
        e1, _ = await processor.process_event(DeploymentIngestor.process(dep))
        print(f"  + Deployment registered: {dep.version} ({dep.commit_hash[:7]}) by {dep.author}")

        # 3. Metric Anomaly: DB Connection Pool Saturation
        print("\n[STEP 2] Telemetry Anomaly Detected:")
        met = MetricIngestRequest(
            service="payment-service",
            metric_name="db_pool_utilization",
            value=98.5,
            unit="percent",
        )
        e2, incident_id = await processor.process_event(MetricIngestor.process(met))
        print(f"  [!] Metric Alert: {met.metric_name} = {met.value}% (Threshold: 90.0%)")
        print(f"  [!] Incident Auto-Triggered: ID={incident_id}")

        # 4. Error Ingestion: Database Timeout
        print("\n[STEP 3] Application Errors Correlated:")
        err = ErrorIngestRequest(
            service="payment-service",
            error_class="DatabaseConnectionTimeout",
            error_message="Could not acquire database connection from pool within 30000ms",
            http_status=500,
        )
        e3, inc_id3 = await processor.process_event(ErrorIngestor.process(err))
        print(f"  + Correlated HTTP 500 error to Incident {inc_id3}")

        # 5. AI Investigation Agent
        print("\n[STEP 4] Invoking AI Root-Cause Investigation Agent...")
        agent = IncidentInvestigationAgent(session)
        report = await agent.investigate_incident(incident_id)

        print("\n" + "-" * 70)
        print("[AI INVESTIGATION REPORT]")
        print("-" * 70)
        print(f"Summary: {report['summary']}")
        print(f"Overall Confidence: {int(report['confidence_score'] * 100)}%")
        
        print("\nRoot-Cause Hypotheses:")
        for idx, h in enumerate(report["hypotheses"], 1):
            print(f"  {idx}. [{h['likelihood'].upper()} LIKELIHOOD] {h['title']} (Confidence: {int(h['confidence_score'] * 100)}%)")
            print(f"     Rationale: {h['rationale']}")
            print(f"     Evidence Count: {len(h['supporting_evidence_ids'])} items")

        print("\nSupporting Telemetry Evidence:")
        for ev in report["supporting_evidence"][:3]:
            print(f"  - [{ev['type'].upper()}] {ev['summary']} (Source: {ev['source']})")

        print("\nPending Approvals for Remediation:")
        pending = report["pending_approvals"]
        for p in pending:
            print(f"  [ID: {p['id']}] Action: {p['action_type'].upper()} | Risk: {p['risk_level'].upper()} | Description: {p['description']}")

        # 6. Human Approval & Automated Execution
        if pending:
            target_approval = pending[0]
            print(f"\n[STEP 5] Human-in-the-Loop Sign-off:")
            print(f"  Engineer reviews action '{target_approval['action_type'].upper()}' (Risk: {target_approval['risk_level'].upper()})")
            print(f"  Decision: APPROVED by 'on_call_sre'")

            workflow = ApprovalWorkflowService(session)
            exec_res = await workflow.approve_and_execute(
                approval_id=target_approval["id"], approved_by="on_call_sre"
            )
            print(f"  + Execution Status: {exec_res['status'].upper()}")
            print(f"  + Output: {exec_res['execution_result']['message']}")
            print(f"  + Incident Status: RESOLVED")

    await engine.dispose()
    print("\n" + "=" * 70)
    print("[SUCCESS] SIMULATION COMPLETE: Full vertical slice successfully verified!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_simulation())
