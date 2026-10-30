from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from backend.app.api import (
    approvals_router,
    health_router,
    incidents_router,
    ingestion_router,
    investigations_router,
    knowledge_router,
    simulator_router,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import async_session_factory, engine, init_db
from backend.app.processing.queue import event_queue
from backend.app.rag.seed_data import seed_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing Production AI Incident Assistant backend...")
    # 1. Initialize DB tables
    await init_db()

    # 2. Seed knowledge base
    async with async_session_factory() as session:
        await seed_knowledge_base(session)

    # 3. Start event queue worker
    await event_queue.start()
    logger.info("Application startup completed successfully.")

    yield

    # Shutdown
    logger.info("Shutting down Application...")
    await event_queue.stop()
    await engine.dispose()
    logger.info("Shutdown completed.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered incident management and root-cause analysis platform.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(ingestion_router, prefix=settings.API_PREFIX)
app.include_router(incidents_router, prefix=settings.API_PREFIX)
app.include_router(investigations_router, prefix=settings.API_PREFIX)
app.include_router(approvals_router, prefix=settings.API_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_PREFIX)
app.include_router(simulator_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix=settings.API_PREFIX)


# Dashboard HTML view served directly from the root
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    from backend.app.dashboard_html import DASHBOARD_HTML
    return HTMLResponse(content=DASHBOARD_HTML)

