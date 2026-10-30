from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.db.session import get_db

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
    }


@router.get("/metrics")
async def system_metrics() -> Dict[str, Any]:
    return {
        "version": "1.0.0",
        "status": "healthy",
        "correlation_window_minutes": settings.CORRELATION_WINDOW_MINUTES,
        "thresholds": {
            "latency_ms": settings.METRIC_LATENCY_THRESHOLD_MS,
            "cpu_percent": settings.METRIC_CPU_THRESHOLD_PERCENT,
            "memory_percent": settings.METRIC_MEMORY_THRESHOLD_PERCENT,
            "db_pool_percent": settings.METRIC_DB_POOL_THRESHOLD_PERCENT,
            "error_rate_percent": settings.METRIC_ERROR_RATE_THRESHOLD_PERCENT,
        },
    }

