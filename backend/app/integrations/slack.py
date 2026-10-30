from typing import Any, Dict, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


class SlackIntegration:
    """Slack Block Kit incident notifier."""

    @staticmethod
    async def send_incident_alert(
        incident_id: str, title: str, service: str, severity: str, summary: str
    ) -> bool:
        if not settings.SLACK_WEBHOOK_URL:
            logger.info(f"[Slack Notification Mock] {severity.upper()} Incident {incident_id}: {title}")
            return True

        severity_emoji = "🚨" if severity == "critical" else "⚠️"
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{severity_emoji} Production Incident: {incident_id}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Service:*\n`{service}`"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n`{severity.upper()}`"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{title}\n\n*AI Summary:*\n{summary}",
                    },
                },
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
                res.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

