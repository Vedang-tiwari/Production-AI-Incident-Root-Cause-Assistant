from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.repositories import ApprovalRepository
from backend.app.db.session import get_db
from backend.app.remediation.approval import ApprovalWorkflowService

router = APIRouter(prefix="/approvals", tags=["Approvals & Remediation"])


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve" or "reject"
    actor: str = "on_call_engineer"
    rejection_reason: Optional[str] = None


@router.get("", response_model=List[Dict[str, Any]])
async def list_approvals(
    status: Optional[str] = Query(None, description="pending, approved, rejected, executed"),
    incident_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    repo = ApprovalRepository(db)
    if incident_id:
        approvals = await repo.list_by_incident(incident_id)
    elif status == "pending":
        approvals = await repo.list_pending()
    else:
        # All approvals
        stmt_approvals = await repo.list_pending()
        approvals = stmt_approvals

    return [
        {
            "id": a.id,
            "incident_id": a.incident_id,
            "action_type": a.action_type,
            "description": a.description,
            "risk_level": a.risk_level,
            "status": a.status,
            "requested_by": a.requested_by,
            "approved_by": a.approved_by,
            "rejection_reason": a.rejection_reason,
            "execution_result": a.execution_result,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "responded_at": a.responded_at.isoformat() if a.responded_at else None,
        }
        for a in approvals
    ]


@router.post("/{approval_id}/action")
async def take_approval_action(
    approval_id: str, req: ApprovalDecisionRequest, db: AsyncSession = Depends(get_db)
):
    workflow = ApprovalWorkflowService(db)
    try:
        if req.decision.lower() == "approve":
            return await workflow.approve_and_execute(approval_id=approval_id, approved_by=req.actor)
        elif req.decision.lower() == "reject":
            return await workflow.reject(
                approval_id=approval_id, rejected_by=req.actor, reason=req.rejection_reason
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid decision '{req.decision}'. Must be 'approve' or 'reject'."
            )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Approval action failed: {str(ex)}")

