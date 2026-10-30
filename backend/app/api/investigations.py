from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.agent import IncidentInvestigationAgent
from backend.app.db.repositories import InvestigationRepository
from backend.app.db.session import get_db

router = APIRouter(prefix="/incidents", tags=["Investigations"])


@router.post("/{incident_id}/investigate", status_code=status.HTTP_200_OK)
async def investigate_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    agent = IncidentInvestigationAgent(db)
    try:
        result = await agent.investigate_incident(incident_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(ex)}")


@router.get("/{incident_id}/investigation")
async def get_latest_investigation(incident_id: str, db: AsyncSession = Depends(get_db)):
    repo = InvestigationRepository(db)
    report = await repo.get_latest_by_incident(incident_id)
    if not report:
        raise HTTPException(
            status_code=404, detail=f"No investigation report found for incident {incident_id}"
        )

    return {
        "id": report.id,
        "incident_id": report.incident_id,
        "summary": report.summary,
        "confidence_score": report.confidence_score,
        "hypotheses": report.hypotheses,
        "supporting_evidence": report.supporting_evidence,
        "recommendations": report.recommendations,
        "uncertainty_factors": report.uncertainty_factors,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }

