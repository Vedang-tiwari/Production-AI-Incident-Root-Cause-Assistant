from backend.app.ingestion.schemas import DeploymentIngestRequest, NormalizedEvent
from backend.app.processing.normalizer import EventNormalizer


class DeploymentIngestor:
    @staticmethod
    def process(request: DeploymentIngestRequest) -> NormalizedEvent:
        return EventNormalizer.normalize_deployment(request)

