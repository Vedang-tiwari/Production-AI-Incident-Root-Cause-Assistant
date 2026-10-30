import pytest
from backend.app.ingestion.schemas import (
    ErrorIngestRequest,
    MetricIngestRequest,
    Severity,
)
from backend.app.processing.anomaly_detector import AnomalyDetector
from backend.app.processing.normalizer import EventNormalizer


def test_detect_db_pool_anomaly():
    req = MetricIngestRequest(
        service="payment-service",
        metric_name="db_pool_utilization",
        value=95.0,
        unit="percent",
    )
    norm = EventNormalizer.normalize_metric(req)
    detector = AnomalyDetector()
    is_anomaly, score, reason = detector.evaluate(norm)
    assert is_anomaly is True
    assert score >= 0.70
    assert "Database connection pool saturation" in reason


def test_detect_latency_anomaly():
    req = MetricIngestRequest(
        service="payment-service",
        metric_name="request_latency_ms",
        value=2500.0,
        unit="ms",
    )
    norm = EventNormalizer.normalize_metric(req)
    detector = AnomalyDetector()
    is_anomaly, score, reason = detector.evaluate(norm)
    assert is_anomaly is True
    assert score >= 0.60
    assert "High latency" in reason


def test_normal_metric_not_anomalous():
    req = MetricIngestRequest(
        service="payment-service",
        metric_name="cpu_percent",
        value=35.0,
        unit="percent",
    )
    norm = EventNormalizer.normalize_metric(req)
    detector = AnomalyDetector()
    is_anomaly, score, reason = detector.evaluate(norm)
    assert is_anomaly is False
    assert score == 0.0


def test_detect_http_500_anomaly():
    req = ErrorIngestRequest(
        service="order-service",
        error_class="DatabaseConnectionTimeout",
        error_message="Connection pool exhausted",
        http_status=500,
    )
    norm = EventNormalizer.normalize_error(req)
    detector = AnomalyDetector()
    is_anomaly, score, reason = detector.evaluate(norm)
    assert is_anomaly is True
    assert score >= 0.80

