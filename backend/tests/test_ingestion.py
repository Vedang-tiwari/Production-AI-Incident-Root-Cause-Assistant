from datetime import datetime, timezone
import pytest
from backend.app.ingestion.schemas import (
    DeploymentIngestRequest,
    ErrorIngestRequest,
    EventType,
    LogIngestRequest,
    MetricIngestRequest,
    OTelIngestRequest,
    OTelSpan,
    Severity,
)
from backend.app.processing.normalizer import EventNormalizer


def test_normalize_log():
    req = LogIngestRequest(
        service="payment-service",
        message="Database connection timeout",
        level="error",
        trace_id="trace-1234",
    )
    norm = EventNormalizer.normalize_log(req)
    assert norm.service == "payment-service"
    assert norm.event_type == EventType.LOG
    assert norm.severity == Severity.HIGH
    assert norm.trace_id == "trace-1234"
    assert "timeout" in norm.message


def test_normalize_error_critical():
    req = ErrorIngestRequest(
        service="order-service",
        error_class="DatabaseConnectionTimeout",
        error_message="Connection pool exhausted",
        http_status=500,
    )
    norm = EventNormalizer.normalize_error(req)
    assert norm.service == "order-service"
    assert norm.event_type == EventType.ERROR
    assert norm.severity == Severity.CRITICAL
    assert "[DatabaseConnectionTimeout]" in norm.message


def test_normalize_metric():
    req = MetricIngestRequest(
        service="payment-service",
        metric_name="db_pool_utilization",
        value=98.5,
        unit="percent",
    )
    norm = EventNormalizer.normalize_metric(req)
    assert norm.service == "payment-service"
    assert norm.event_type == EventType.METRIC
    assert norm.payload["value"] == 98.5


def test_normalize_deployment():
    req = DeploymentIngestRequest(
        service="auth-service",
        version="v1.4.0",
        commit_hash="abcdef123456",
        author="eng@example.com",
        status="completed",
    )
    norm = EventNormalizer.normalize_deployment(req)
    assert norm.service == "auth-service"
    assert norm.event_type == EventType.DEPLOYMENT
    assert norm.payload["version"] == "v1.4.0"


def test_normalize_otel_span():
    span = OTelSpan(
        trace_id="trace-abc",
        span_id="span-1",
        name="POST /v1/charge",
        status_code="ERROR",
        status_message="Database failure",
    )
    norm = EventNormalizer.normalize_otel_span(span, service="payment-service", environment="production")
    assert norm.event_type == EventType.OTEL
    assert norm.severity == Severity.CRITICAL
    assert norm.trace_id == "trace-abc"

