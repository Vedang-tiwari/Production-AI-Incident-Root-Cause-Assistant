from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Production AI Incident & Root-Cause Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-incident-assistant-3012"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./incident_assistant.db"

    # Redis (Optional)
    REDIS_URL: Optional[str] = None

    # AI / LLM Configuration
    LLM_PROVIDER: str = "mock_fallback"  # "mock_fallback", "openai", "gemini"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1

    # Observability & External Integrations
    SLACK_WEBHOOK_URL: Optional[str] = None
    TEAMS_WEBHOOK_URL: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO: Optional[str] = None

    # Thresholds for Anomaly Detection
    METRIC_LATENCY_THRESHOLD_MS: float = 1000.0
    METRIC_CPU_THRESHOLD_PERCENT: float = 85.0
    METRIC_MEMORY_THRESHOLD_PERCENT: float = 90.0
    METRIC_DB_POOL_THRESHOLD_PERCENT: float = 90.0
    METRIC_ERROR_RATE_THRESHOLD_PERCENT: float = 5.0

    # Correlation Window in Minutes
    CORRELATION_WINDOW_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

