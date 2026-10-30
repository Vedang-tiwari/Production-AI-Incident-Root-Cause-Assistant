from backend.app.ingestion.schemas import ErrorIngestRequest, NormalizedEvent
from backend.app.processing.normalizer import EventNormalizer


class ErrorIngestor:
    @staticmethod
    def process(request: ErrorIngestRequest) -> NormalizedEvent:
        return EventNormalizer.normalize_error(request)

