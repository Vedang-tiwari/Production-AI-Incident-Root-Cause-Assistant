from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.context_builder import IncidentContextBuilder
from backend.app.ai.investigation import ai_investigation_engine
from backend.app.ai.root_cause import InvestigationReportOutput
from backend.app.ai.tools.deployment_analysis import DeploymentAnalysisTool
from backend.app.ai.tools.knowledge_tools import (
    HistoricalRetrievalTool,
    RunbookRetrievalTool,
)
from backend.app.ai.tools.log_search import LogSearchTool
from backend.app.ai.tools.metrics_analysis import MetricsAnalysisTool
from backend.app.core.logging import logger
from backend.app.db.models import ApprovalRequest, Incident, InvestigationReport, TimelineEvent
from backend.app.db.repositories import (
    ApprovalRepository,
    AuditRepository,
    IncidentRepository,
    InvestigationRepository,
    TimelineRepository,
)


class IncidentInvestigationAgent:
    """
    Coordinates tool-assisted investigation of incidents, invokes AI reasoning,
    persists investigation reports, and generates human approval requests.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.context_builder = IncidentContextBuilder(db)
        self.incident_repo = IncidentRepository(db)
        self.investigation_repo = InvestigationRepository(db)
        self.approval_repo = ApprovalRepository(db)
        self.timeline_repo = TimelineRepository(db)
        self.audit_repo = AuditRepository(db)

        # Tools
        self.log_tool = LogSearchTool(db)
        self.metrics_tool = MetricsAnalysisTool(db)
        self.deployment_tool = DeploymentAnalysisTool(db)
        self.historical_tool = HistoricalRetrievalTool(db)
        self.runbook_tool = RunbookRetrievalTool(db)

    async def investigate_incident(self, incident_id: str) -> Dict[str, Any]:
        incident = await self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found.")

        logger.info(f"AI Agent starting investigation for incident {incident_id}")

        # 1. Update incident status to 'investigating'
        incident.status = "investigating"
        await self.db.commit()

        # Add timeline event: Investigation Started
        await self.timeline_repo.add_entry(
            TimelineEvent(
                incident_id=incident_id,
                timestamp=datetime.now(timezone.utc),
                event_type="investigation_started",
                title="AI Investigation Started",
                description="AI Investigation Agent initialized; analyzing correlated telemetry, deployments, and runbooks.",
            )
        )

        # 2. Build structured investigation context
        context = await self.context_builder.build_context(incident)

        # 3. Corroborate with tools
        recent_logs = await self.log_tool.run(service=incident.service, limit=15)
        metrics_summary = await self.metrics_tool.run(service=incident.service)
        recent_deploys = await self.deployment_tool.run(service=incident.service, limit=3)

        context["tool_corroboration"] = {
            "recent_logs": recent_logs,
            "metrics_summary": metrics_summary,
            "recent_deploys": recent_deploys,
        }

        # 4. Generate Root Cause Investigation Report
        report_output: InvestigationReportOutput = await ai_investigation_engine.generate_investigation(context)

        # 5. Persist Investigation Report in DB
        db_report = InvestigationReport(
            incident_id=incident_id,
            summary=report_output.summary,
            hypotheses=[h.model_dump() for h in report_output.hypotheses],
            supporting_evidence=[e.model_dump() for e in report_output.supporting_evidence],
            recommendations=[r.model_dump() for r in report_output.recommendations],
            confidence_score=report_output.confidence_score,
            uncertainty_factors=report_output.uncertainty_factors,
            created_at=datetime.now(timezone.utc),
        )
        saved_report = await self.investigation_repo.create(db_report)

        # 6. Update Incident Status to 'identified'
        top_hypothesis = report_output.hypotheses[0].title if report_output.hypotheses else "Unknown cause"
        incident.status = "identified"
        incident.confirmed_root_cause = top_hypothesis
        await self.db.commit()

        # 7. Add timeline event: Root Cause Identified
        await self.timeline_repo.add_entry(
            TimelineEvent(
                incident_id=incident_id,
                timestamp=datetime.now(timezone.utc),
                event_type="hypothesis_formed",
                title=f"Root Cause Identified: {top_hypothesis}",
                description=report_output.summary,
                source_ref=saved_report.id,
                metadata_json={
                    "confidence_score": report_output.confidence_score,
                    "hypotheses_count": len(report_output.hypotheses),
                },
            )
        )

        # 8. Create Approval Requests for recommendations requiring approval
        created_approvals = []
        for rec in report_output.recommendations:
            if rec.requires_approval:
                req = ApprovalRequest(
                    incident_id=incident_id,
                    action_type=rec.action,
                    description=rec.description,
                    risk_level=rec.risk_level.lower(),
                    status="pending",
                    requested_by="ai_investigation_agent",
                    execution_result={"command": rec.command_or_script},
                )
                saved_req = await self.approval_repo.create(req)
                created_approvals.append(saved_req)

                # Add timeline entry
                await self.timeline_repo.add_entry(
                    TimelineEvent(
                        incident_id=incident_id,
                        timestamp=datetime.now(timezone.utc),
                        event_type="approval_requested",
                        title=f"Approval Requested: {rec.action.upper()}",
                        description=f"Action '{rec.description}' (Risk: {rec.risk_level}) requires human sign-off.",
                        source_ref=saved_req.id,
                    )
                )

        # 9. Log audit trail
        await self.audit_repo.log_action(
            actor="ai_investigation_agent",
            action="investigation_completed",
            details={
                "incident_id": incident_id,
                "report_id": saved_report.id,
                "confidence_score": report_output.confidence_score,
                "hypotheses_count": len(report_output.hypotheses),
                "approval_requests_count": len(created_approvals),
            },
            incident_id=incident_id,
        )

        logger.info(f"AI Agent completed investigation for incident {incident_id}")

        return {
            "incident_id": incident_id,
            "status": incident.status,
            "report_id": saved_report.id,
            "summary": report_output.summary,
            "confidence_score": report_output.confidence_score,
            "hypotheses": [h.model_dump() for h in report_output.hypotheses],
            "supporting_evidence": [e.model_dump() for e in report_output.supporting_evidence],
            "recommendations": [r.model_dump() for r in report_output.recommendations],
            "uncertainty_factors": report_output.uncertainty_factors,
            "pending_approvals": [
                {
                    "id": a.id,
                    "action_type": a.action_type,
                    "description": a.description,
                    "risk_level": a.risk_level,
                    "status": a.status,
                }
                for a in created_approvals
            ],
        }

