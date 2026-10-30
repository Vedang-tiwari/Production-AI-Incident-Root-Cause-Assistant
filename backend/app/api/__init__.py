from backend.app.api.approvals import router as approvals_router
from backend.app.api.health import router as health_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.investigations import router as investigations_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.simulator import router as simulator_router

__all__ = [
    "ingestion_router",
    "incidents_router",
    "investigations_router",
    "approvals_router",
    "knowledge_router",
    "simulator_router",
    "health_router",
]

