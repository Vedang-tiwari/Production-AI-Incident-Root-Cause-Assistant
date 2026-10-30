from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.rag.embeddings import embedding_generator


class VectorDocument(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    vector: List[float] = Field(default_factory=list)


class VectorSearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float


class InMemoryVectorStore:
    def __init__(self):
        self._collections: Dict[str, Dict[str, VectorDocument]] = {
            "runbooks": {},
            "historical_incidents": {},
        }

    def add_document(
        self,
        collection: str,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        vector: Optional[List[float]] = None,
    ) -> VectorDocument:
        if collection not in self._collections:
            self._collections[collection] = {}

        if not vector:
            vector = embedding_generator.generate_embedding(content)

        doc = VectorDocument(
            id=doc_id,
            content=content,
            metadata=metadata or {},
            vector=vector,
        )
        self._collections[collection][doc_id] = doc
        return doc

    def search(
        self,
        collection: str,
        query: str,
        service: Optional[str] = None,
        top_k: int = 3,
        threshold: float = 0.1,
    ) -> List[VectorSearchResult]:
        if collection not in self._collections:
            return []

        query_vector = embedding_generator.generate_embedding(query)
        candidates = list(self._collections[collection].values())

        results = []
        for doc in candidates:
            # Metadata filter by service if specified and not matching 'all'
            doc_service = doc.metadata.get("service")
            if service and doc_service and doc_service != "all" and doc_service != service:
                # Still check if generic
                pass

            sim = embedding_generator.cosine_similarity(query_vector, doc.vector)
            
            # Boost score if service directly matches
            if service and doc_service and doc_service.lower() == service.lower():
                sim = min(sim + 0.15, 1.0)

            if sim >= threshold:
                results.append(
                    VectorSearchResult(
                        id=doc.id,
                        content=doc.content,
                        metadata=doc.metadata,
                        score=sim,
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def clear(self, collection: Optional[str] = None) -> None:
        if collection and collection in self._collections:
            self._collections[collection].clear()
        else:
            for k in self._collections:
                self._collections[k].clear()


vector_store = InMemoryVectorStore()

