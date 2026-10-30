from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.logging import logger
from backend.app.db.models import ApprovalRequest, TimelineEvent
from backend.app.db.repositories import (
    ApprovalRepository,
    AuditRepository,
    TimelineRepository,
)
from backend.app.remediation.executor import RemediationExecutor


class ApprovalWorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.approval_repo = ApprovalRepository(db)
        self.timeline_repo = TimelineRepository(db)
        self.audit_repo = AuditRepository(db)
        self.executor = RemediationExecutor(db)

    async def approve_and_execute(
        self, approval_id: str, approved_by: str = "engineer"
    ) -> Dict[str, Any]:
        approval = await self.approval_repo.get_by_id(approval_id)
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")

        if approval.status != "pending":
            raise ValueError(f"Approval request {approval_id} is already in state '{approval.status}'.")

        logger.info(f"Action {approval.action_type} for incident {approval.incident_id} APPROVED by {approved_by}")

        # Mark as approved
        approval = await self.approval_repo.update_decision(
            approval_id=approval_id,
            status="approved",
            approved_by=approved_by,
        )

        # Timeline event: Approved
        await self.timeline_repo.add_entry(
            TimelineEvent(
                incident_id=approval.incident_id,
                timestamp=datetime.now(timezone.utc),
                event_type="approval_granted",
                title=f"Action Approved: {approval.action_type.upper()}",
                description=f"Approved by {approved_by}: {approval.description}",
                source_ref=approval.id,
            )
        )

        # Audit log
        await self.audit_repo.log_action(
            actor=approved_by,
            action="approval_granted",
            details={
                "approval_id": approval_id,
                "action": approval.action_type,
            },
            incident_id=approval.incident_id,
        )

        # Automatically execute approved action
        exec_result = await self.executor.execute_action(approval, executed_by=approved_by)

        return {
            "approval_id": approval.id,
            "incident_id": approval.incident_id,
            "status": "executed",
            "approved_by": approved_by,
            "execution_result": exec_result,
        }

    async def reject(
        self, approval_id: str, rejected_by: str = "engineer", reason: Optional[str] = None
    ) -> Dict[str, Any]:
        approval = await self.approval_repo.get_by_id(approval_id)
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")

        if approval.status != "pending":
            raise ValueError(f"Approval request {approval_id} is already in state '{approval.status}'.")

        logger.info(f"Action {approval.action_type} for incident {approval.incident_id} REJECTED by {rejected_by}")

        approval = await self.approval_repo.update_decision(
            approval_id=approval_id,
            status="rejected",
            approved_by=rejected_by,
            rejection_reason=reason or "Rejected by engineer.",
        )

        # Timeline event
        await self.timeline_repo.add_entry(
            TimelineEvent(
                incident_id=approval.incident_id,
                timestamp=datetime.now(timezone.utc),
                event_type="approval_rejected",
                title=f"Action Rejected: {approval.action_type.upper()}",
                description=f"Rejected by {rejected_by}: {reason or 'No reason provided.'}",
                source_ref=approval.id,
            )
        )

        # Audit log
        await self.audit_repo.log_action(
            actor=rejected_by,
            action="approval_rejected",
            details={
                "approval_id": approval_id,
                "action": approval.action_type,
                "reason": reason,
            },
            incident_id=approval.incident_id,
        )

        return {
            "approval_id": approval.id,
            "incident_id": approval.incident_id,
            "status": "rejected",
            "rejected_by": rejected_by,
            "reason": reason,
        }

