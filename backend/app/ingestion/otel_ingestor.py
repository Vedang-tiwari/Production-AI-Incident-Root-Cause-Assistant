from typing import List
from backend.app.ingestion.schemas import NormalizedEvent, OTelIngestRequest
from backend.app.processing.normalizer import EventNormalizer


class OTelIngestor:
    @staticmethod
    def process(request: OTelIngestRequest) -> List[NormalizedEvent]:
        events = []
        for span in request.spans:
            events.append(
                EventNormalizer.normalize_otel_span(
                    span=span,
                    service=request.service,
                    environment=request.environment,
                )
            )
        return events

