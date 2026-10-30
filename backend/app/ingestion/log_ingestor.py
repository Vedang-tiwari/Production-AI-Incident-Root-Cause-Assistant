from backend.app.ingestion.schemas import LogIngestRequest, NormalizedEvent
from backend.app.processing.normalizer import EventNormalizer


class LogIngestor:
    @staticmethod
    def process(request: LogIngestRequest) -> NormalizedEvent:
        return EventNormalizer.normalize_log(request)

