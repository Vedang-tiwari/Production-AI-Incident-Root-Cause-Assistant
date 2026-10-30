from typing import Tuple
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ingestion.schemas import EventType, NormalizedEvent, Severity


class AnomalyDetector:
    """
    Evaluates incoming normalized events against statistical and threshold rules
    to detect operational anomalies.
    """

    @staticmethod
    def evaluate(event: NormalizedEvent) -> Tuple[bool, float, str]:
        """
        Returns: (is_anomaly, anomaly_score, reason)
        anomaly_score is normalized between 0.0 and 1.0.
        """
        is_anomaly = False
        anomaly_score = 0.0
        reason = ""

        # 1. Metric anomaly detection
        if event.event_type == EventType.METRIC:
            metric_name = event.payload.get("metric_name", "").lower()
            val = float(event.payload.get("value", 0.0))

            if "latency" in metric_name:
                if val >= settings.METRIC_LATENCY_THRESHOLD_MS:
                    is_anomaly = True
                    ratio = min(val / settings.METRIC_LATENCY_THRESHOLD_MS, 3.0)
                    anomaly_score = min(0.6 + (ratio - 1.0) * 0.2, 1.0)
                    reason = f"High latency detected: {val:.1f}ms exceeds threshold of {settings.METRIC_LATENCY_THRESHOLD_MS}ms"

            elif "pool" in metric_name or "db_connection" in metric_name or "connections" in metric_name:
                if val >= settings.METRIC_DB_POOL_THRESHOLD_PERCENT:
                    is_anomaly = True
                    anomaly_score = min(0.7 + (val - settings.METRIC_DB_POOL_THRESHOLD_PERCENT) / 30.0, 1.0)
                    reason = f"Database connection pool saturation: {val:.1f}% exceeds threshold of {settings.METRIC_DB_POOL_THRESHOLD_PERCENT}%"

            elif "cpu" in metric_name:
                if val >= settings.METRIC_CPU_THRESHOLD_PERCENT:
                    is_anomaly = True
                    anomaly_score = min(0.6 + (val - settings.METRIC_CPU_THRESHOLD_PERCENT) / 40.0, 1.0)
                    reason = f"High CPU utilization: {val:.1f}% exceeds threshold of {settings.METRIC_CPU_THRESHOLD_PERCENT}%"

            elif "memory" in metric_name or "mem" in metric_name:
                if val >= settings.METRIC_MEMORY_THRESHOLD_PERCENT:
                    is_anomaly = True
                    anomaly_score = min(0.7 + (val - settings.METRIC_MEMORY_THRESHOLD_PERCENT) / 30.0, 1.0)
                    reason = f"Memory exhaustion alert: {val:.1f}% exceeds threshold of {settings.METRIC_MEMORY_THRESHOLD_PERCENT}%"

            elif "error_rate" in metric_name:
                if val >= settings.METRIC_ERROR_RATE_THRESHOLD_PERCENT:
                    is_anomaly = True
                    anomaly_score = min(0.8 + (val - settings.METRIC_ERROR_RATE_THRESHOLD_PERCENT) / 50.0, 1.0)
                    reason = f"Elevated error rate: {val:.1f}% exceeds threshold of {settings.METRIC_ERROR_RATE_THRESHOLD_PERCENT}%"

        # 2. Application Error anomaly detection
        elif event.event_type == EventType.ERROR:
            http_status = event.payload.get("http_status")
            error_class = event.payload.get("error_class", "").lower()
            error_message = event.payload.get("error_message", "").lower()

            critical_keywords = [
                "timeout",
                "connection refused",
                "deadlock",
                "outofmemory",
                "pool exhausted",
                "circuit breaker open",
                "fatal",
                "segmentation fault",
            ]

            matches_keyword = any(kw in error_class or kw in error_message for kw in critical_keywords)

            if http_status and http_status >= 500:
                is_anomaly = True
                anomaly_score = 0.85 if matches_keyword else 0.70
                reason = f"Critical HTTP {http_status} server error: {event.message}"
            elif matches_keyword or event.severity == Severity.CRITICAL:
                is_anomaly = True
                anomaly_score = 0.80
                reason = f"Critical exception pattern detected: {event.message}"

        # 3. Deployment status anomaly
        elif event.event_type == EventType.DEPLOYMENT:
            status = event.payload.get("status", "").lower()
            if status in ["failed", "rolled_back"]:
                is_anomaly = True
                anomaly_score = 0.75
                reason = f"Deployment anomaly: {event.message}"

        # 4. OpenTelemetry span failure anomaly
        elif event.event_type == EventType.OTEL:
            status_code = event.payload.get("status_code", "").upper()
            if status_code == "ERROR":
                is_anomaly = True
                anomaly_score = 0.75
                reason = f"OTel trace span error: {event.message}"

        if is_anomaly:
            event.is_anomaly = True
            event.anomaly_score = round(anomaly_score, 2)
            if event.severity in [Severity.INFO, Severity.LOW]:
                event.severity = Severity.HIGH if anomaly_score >= 0.75 else Severity.MEDIUM

        return is_anomaly, round(anomaly_score, 2), reason

