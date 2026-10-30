import asyncio
from typing import Any, Callable, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ingestion.schemas import NormalizedEvent


class EventQueue:
    """
    Asynchronous event queue.
    Uses in-memory asyncio.Queue by default, supporting Redis queue if configured.
    """

    def __init__(self):
        self._queue: asyncio.Queue[NormalizedEvent] = asyncio.Queue()
        self._handlers: List[Callable[[NormalizedEvent], Any]] = []
        self._running: bool = False
        self._worker_task: Optional[asyncio.Task] = None

    def register_handler(self, handler: Callable[[NormalizedEvent], Any]) -> None:
        self._handlers.append(handler)

    async def enqueue(self, event: NormalizedEvent) -> None:
        await self._queue.put(event)

    async def enqueue_batch(self, events: List[NormalizedEvent]) -> None:
        for ev in events:
            await self._queue.put(ev)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("EventQueue worker started.")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("EventQueue worker stopped.")

    async def _worker(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                for handler in self._handlers:
                    try:
                        res = handler(event)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as ex:
                        logger.error(f"Error in event handler: {ex}", exc_info=True)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in event worker: {e}", exc_info=True)


event_queue = EventQueue()

