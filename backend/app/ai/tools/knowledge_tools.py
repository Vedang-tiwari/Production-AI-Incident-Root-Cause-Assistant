from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.rag.retriever import KnowledgeRetriever


class HistoricalRetrievalTool:
    name = "historical_retrieval"
    description = "Searches resolved historical incidents with similar error signatures and root causes."

    def __init__(self, db: AsyncSession):
        self.retriever = KnowledgeRetriever(db)

    async def run(self, query: str, service: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return await self.retriever.retrieve_historical_incidents(
            query=query, service=service, top_k=top_k
        )


class RunbookRetrievalTool:
    name = "runbook_retrieval"
    description = "Retrieves relevant operational runbooks and troubleshooting guides for the failure mode."

    def __init__(self, db: AsyncSession):
        self.retriever = KnowledgeRetriever(db)

    async def run(self, query: str, service: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return await self.retriever.retrieve_runbooks(
            query=query, service=service, top_k=top_k
        )

