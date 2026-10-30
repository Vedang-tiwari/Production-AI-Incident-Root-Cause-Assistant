from typing import Any, Dict, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


class TeamsIntegration:
    """Microsoft Teams adaptive card notifier."""

    @staticmethod
    async def send_incident_alert(
        incident_id: str, title: str, service: str, severity: str, summary: str
    ) -> bool:
        if not settings.TEAMS_WEBHOOK_URL:
            logger.info(f"[Teams Notification Mock] {severity.upper()} Incident {incident_id}: {title}")
            return True

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "D70000" if severity == "critical" else "FF9900",
            "summary": f"Incident {incident_id}: {title}",
            "sections": [
                {
                    "activityTitle": f"Production Incident: {incident_id}",
                    "activitySubtitle": f"Service: {service} | Severity: {severity.upper()}",
                    "text": summary,
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(settings.TEAMS_WEBHOOK_URL, json=payload)
                res.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Teams alert: {e}")
            return False


class GitHubIntegration:
    """GitHub Issue Creator for incident tracking."""

    @staticmethod
    async def create_issue(title: str, body: str, labels: Optional[list] = None) -> Optional[str]:
        if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO:
            logger.info(f"[GitHub Mock] Issue would be created: '{title}' in repo '{settings.GITHUB_REPO or 'mock/repo'}'")
            return "https://github.com/mock-org/repo/issues/101"

        url = f"https://api.github.com/repos/{settings.GITHUB_REPO}/issues"
        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {
            "title": title,
            "body": body,
            "labels": labels or ["incident", "production-outage"],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                return data.get("html_url")
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return None

