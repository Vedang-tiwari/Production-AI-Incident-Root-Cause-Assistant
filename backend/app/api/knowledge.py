from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import HistoricalIncident, Runbook
from backend.app.db.repositories import KnowledgeRepository
from backend.app.db.session import get_db
from backend.app.rag.embeddings import embedding_generator
from backend.app.rag.retriever import KnowledgeRetriever
from backend.app.rag.vector_store import vector_store

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & RAG"])


class RunbookCreateRequest(BaseModel):
    id: str
    title: str
    service: str = "all"
    category: str = "troubleshooting"
    tags: List[str] = Field(default_factory=list)
    content_markdown: str


class KnowledgeSearchRequest(BaseModel):
    query: str
    service: Optional[str] = None
    top_k: int = 3


@router.get("/runbooks")
async def list_runbooks(
    service: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    runbooks = await repo.get_all_runbooks(service=service)
    return [
        {
            "id": r.id,
            "title": r.title,
            "service": r.service,
            "category": r.category,
            "tags": r.tags,
            "content_markdown": r.content_markdown,
        }
        for r in runbooks
    ]


@router.post("/runbooks", status_code=status.HTTP_201_CREATED)
async def create_runbook(
    req: RunbookCreateRequest, db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    vec = embedding_generator.generate_embedding(
        f"{req.title} {' '.join(req.tags)} {req.content_markdown}"
    )
    rb = Runbook(
        id=req.id,
        title=req.title,
        service=req.service,
        category=req.category,
        tags=req.tags,
        content_markdown=req.content_markdown,
        embedding_vector=vec,
    )
    saved = await repo.add_runbook(rb)
    vector_store.add_document(
        collection="runbooks",
        doc_id=rb.id,
        content=f"{rb.title}\n{rb.content_markdown}",
        metadata={
            "id": rb.id,
            "title": rb.title,
            "service": rb.service,
            "category": rb.category,
            "tags": rb.tags,
        },
        vector=vec,
    )
    return {"status": "created", "id": saved.id, "title": saved.title}


@router.get("/historical")
async def list_historical_incidents(
    service: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    incidents = await repo.get_all_historical_incidents(service=service)
    return [
        {
            "id": h.id,
            "title": h.title,
            "service": h.service,
            "root_cause": h.root_cause,
            "resolution": h.resolution,
            "error_signatures": h.error_signatures,
            "resolved_at": h.resolved_at.isoformat() if h.resolved_at else None,
        }
        for h in incidents
    ]


@router.post("/search")
async def search_knowledge(
    req: KnowledgeSearchRequest, db: AsyncSession = Depends(get_db)
):
    retriever = KnowledgeRetriever(db)
    runbooks = await retriever.retrieve_runbooks(
        query=req.query, service=req.service, top_k=req.top_k
    )
    historical = await retriever.retrieve_historical_incidents(
        query=req.query, service=req.service, top_k=req.top_k
    )
    return {
        "query": req.query,
        "service": req.service,
        "matched_runbooks": runbooks,
        "similar_historical_incidents": historical,
    }

