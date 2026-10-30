from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.logging import logger
from backend.app.db.repositories import KnowledgeRepository
from backend.app.rag.vector_store import VectorSearchResult, vector_store


class KnowledgeRetriever:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = KnowledgeRepository(db)

    async def retrieve_runbooks(
        self, query: str, service: Optional[str] = None, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches vector store for relevant runbooks, falling back to database if empty."""
        results = vector_store.search(
            collection="runbooks",
            query=query,
            service=service,
            top_k=top_k,
        )

        if not results:
            # Fallback to database query by service or tags
            db_runbooks = await self.repo.get_all_runbooks(service=service)
            return [
                {
                    "id": rb.id,
                    "title": rb.title,
                    "service": rb.service,
                    "category": rb.category,
                    "content": rb.content_markdown,
                    "score": 0.5,
                }
                for rb in db_runbooks[:top_k]
            ]

        return [
            {
                "id": r.id,
                "title": r.metadata.get("title", ""),
                "service": r.metadata.get("service", ""),
                "category": r.metadata.get("category", ""),
                "content": r.content,
                "score": r.score,
            }
            for r in results
        ]

    async def retrieve_historical_incidents(
        self, query: str, service: Optional[str] = None, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches vector store for similar past incidents."""
        results = vector_store.search(
            collection="historical_incidents",
            query=query,
            service=service,
            top_k=top_k,
        )

        if not results:
            db_hist = await self.repo.get_all_historical_incidents(service=service)
            return [
                {
                    "id": h.id,
                    "title": h.title,
                    "service": h.service,
                    "root_cause": h.root_cause,
                    "resolution": h.resolution,
                    "score": 0.5,
                }
                for h in db_hist[:top_k]
            ]

        return [
            {
                "id": r.id,
                "title": r.metadata.get("title", ""),
                "service": r.metadata.get("service", ""),
                "root_cause": r.metadata.get("root_cause", ""),
                "resolution": r.metadata.get("resolution", ""),
                "score": r.score,
            }
            for r in results
        ]

