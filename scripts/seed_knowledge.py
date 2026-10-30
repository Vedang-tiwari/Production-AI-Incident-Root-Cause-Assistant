import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from backend.app.core.logging import logger
from backend.app.db.session import async_session_factory, engine, init_db
from backend.app.rag.seed_data import seed_knowledge_base


async def main():
    logger.info("Initializing database tables...")
    await init_db()

    logger.info("Seeding runbooks and historical incidents...")
    async with async_session_factory() as session:
        await seed_knowledge_base(session)

    await engine.dispose()
    logger.info("Knowledge base seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
