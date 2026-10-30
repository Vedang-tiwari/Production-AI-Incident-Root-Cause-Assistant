from backend.app.ingestion.schemas import MetricIngestRequest, NormalizedEvent
from backend.app.processing.normalizer import EventNormalizer


class MetricIngestor:
    @staticmethod
    def process(request: MetricIngestRequest) -> NormalizedEvent:
        return EventNormalizer.normalize_metric(request)

