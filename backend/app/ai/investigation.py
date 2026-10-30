from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ai.prompts import INVESTIGATION_SYSTEM_PROMPT, INVESTIGATION_USER_PROMPT
from backend.app.ai.root_cause import (
    InvestigationReportOutput,
    RecommendedRemediation,
    RootCauseHypothesis,
    SupportingEvidenceItem,
)


class AIInvestigationEngine:
    """
    AI Investigation Engine.
    Coordinates evidence gathering and root-cause reasoning using LLM APIs
    or the deterministic Expert SRE Reasoning Engine.
    """

    async def generate_investigation(self, context: Dict[str, Any]) -> InvestigationReportOutput:
        """Runs the investigation reasoning pipeline."""
        if settings.LLM_PROVIDER in ["openai", "gemini"] and settings.LLM_API_KEY:
            try:
                return await self._call_llm(context)
            except Exception as e:
                logger.error(f"LLM API call failed ({e}). Falling back to Expert Reasoning Engine.", exc_info=True)
                return self._expert_reasoning_fallback(context)

        return self._expert_reasoning_fallback(context)

    async def _call_llm(self, context: Dict[str, Any]) -> InvestigationReportOutput:
        """Calls external LLM endpoint with structured schema instructions."""
        incident = context.get("incident", {})
        errors_str = json.dumps(context.get("sample_errors", []), indent=2)
        deploys_str = json.dumps(context.get("recent_deployments", []), indent=2)
        metrics_str = json.dumps(context.get("metrics", []), indent=2)
        hist_str = json.dumps(context.get("similar_historical_incidents", []), indent=2)
        runbooks_str = json.dumps(context.get("retrieved_runbooks", []), indent=2)

        prompt = INVESTIGATION_USER_PROMPT.format(
            service=incident.get("service", "unknown"),
            title=incident.get("title", "unknown"),
            description=incident.get("description", ""),
            severity=incident.get("severity", "medium"),
            anomalies_and_errors=errors_str,
            recent_deployments=deploys_str,
            metrics_telemetry=metrics_str,
            historical_incidents=hist_str,
            runbooks=runbooks_str,
        )

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": INVESTIGATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": settings.LLM_TEMPERATURE,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            return InvestigationReportOutput(**parsed)

    def _expert_reasoning_fallback(self, context: Dict[str, Any]) -> InvestigationReportOutput:
        """
        Deterministic, evidence-grounded Expert SRE Reasoning Engine.
        Analyzes actual telemetry events, deployments, errors, and RAG knowledge.
        """
        incident = context.get("incident", {})
        service = incident.get("service", "unknown-service")
        sample_errors = context.get("sample_errors", [])
        anomalies = context.get("anomalies", [])
        deployments = context.get("recent_deployments", [])
        metrics = context.get("metrics", [])
        hist_incidents = context.get("similar_historical_incidents", [])
        runbooks = context.get("retrieved_runbooks", [])

        # Collect evidence items
        evidence_items: List[SupportingEvidenceItem] = []
        evidence_ids: List[str] = []

        # 1. Error evidence
        for err in sample_errors:
            item = SupportingEvidenceItem(
                id=err.get("id", f"err-{len(evidence_items)}"),
                type="error",
                timestamp=err.get("timestamp"),
                source=f"{service} error tracker",
                summary=err.get("message", "Application error"),
            )
            evidence_items.append(item)
            evidence_ids.append(item.id)

        # 2. Metric evidence
        db_pool_saturated = False
        high_latency = False
        high_memory = False
        high_cpu = False

        for m in metrics:
            m_name = (m.get("metric_name") or "").lower()
            val = float(m.get("value") or 0.0)
            unit = m.get("unit") or ""

            if "pool" in m_name or "connection" in m_name:
                if val >= settings.METRIC_DB_POOL_THRESHOLD_PERCENT:
                    db_pool_saturated = True
            elif "latency" in m_name:
                if val >= settings.METRIC_LATENCY_THRESHOLD_MS:
                    high_latency = True
            elif "mem" in m_name:
                if val >= settings.METRIC_MEMORY_THRESHOLD_PERCENT:
                    high_memory = True
            elif "cpu" in m_name:
                if val >= settings.METRIC_CPU_THRESHOLD_PERCENT:
                    high_cpu = True

            item = SupportingEvidenceItem(
                id=m.get("id", f"met-{len(evidence_items)}"),
                type="metric",
                timestamp=m.get("timestamp"),
                source=f"{service} telemetry",
                summary=f"Metric {m_name}: {val} {unit}",
            )
            evidence_items.append(item)
            evidence_ids.append(item.id)

        # 3. Deployment evidence
        has_recent_deploy = len(deployments) > 0
        latest_deploy = deployments[0] if has_recent_deploy else None
        if latest_deploy:
            item = SupportingEvidenceItem(
                id=latest_deploy.get("id", f"dep-{len(evidence_items)}"),
                type="deployment",
                timestamp=latest_deploy.get("timestamp"),
                source="CI/CD deployment pipeline",
                summary=f"Deployed {latest_deploy.get('version')} ({latest_deploy.get('commit_hash', '')[:7]}) - Status: {latest_deploy.get('status')}",
            )
            evidence_items.append(item)
            evidence_ids.append(item.id)

        # Synthesize Hypotheses based on gathered evidence
        hypotheses: List[RootCauseHypothesis] = []
        recommendations: List[RecommendedRemediation] = []
        uncertainty: List[str] = []

        all_err_text = " ".join([e.get("message", "").lower() for e in sample_errors] + [incident.get("description", "").lower()])

        # Hypothesis 1: Database Connection Pool Exhaustion
        if db_pool_saturated or "pool" in all_err_text or "connection timeout" in all_err_text:
            conf = 0.88 if (db_pool_saturated and has_recent_deploy) else 0.78
            rationale_msg = (
                f"The service is experiencing database connection timeouts coinciding with connection pool saturation. "
            )
            if has_recent_deploy:
                rationale_msg += f"Recent deployment {latest_deploy.get('version')} may have introduced leaked unclosed database connections or missing connection pooling configurations."

            hypotheses.append(
                RootCauseHypothesis(
                    title="Database Connection Pool Exhaustion",
                    likelihood="High",
                    confidence_score=conf,
                    rationale=rationale_msg,
                    supporting_evidence_ids=evidence_ids[:4],
                )
            )

            if has_recent_deploy:
                recommendations.append(
                    RecommendedRemediation(
                        action="rollback",
                        risk_level="Medium",
                        description=f"Roll back {service} deployment from {latest_deploy.get('version')} to previous release.",
                        requires_approval=True,
                        command_or_script=f"kubectl rollout undo deployment/{service}",
                    )
                )

            recommendations.append(
                RecommendedRemediation(
                    action="scale_pool",
                    risk_level="Low",
                    description=f"Temporarily increase database connection pool capacity by 50% for {service}.",
                    requires_approval=True,
                    command_or_script=f"python scripts/manage_pool.py --service {service} --action increase --percent 50",
                )
            )

        # Hypothesis 2: Memory Leak / Resource Starvation
        elif high_memory or "oom" in all_err_text or "heap" in all_err_text:
            hypotheses.append(
                RootCauseHypothesis(
                    title="Memory Leak & Garbage Collection Starvation",
                    likelihood="High",
                    confidence_score=0.84,
                    rationale=f"Service memory utilization exceeded critical thresholds, triggering elevated GC pauses and request timeouts.",
                    supporting_evidence_ids=evidence_ids[:3],
                )
            )
            if has_recent_deploy:
                recommendations.append(
                    RecommendedRemediation(
                        action="rollback",
                        risk_level="Medium",
                        description=f"Roll back deployment {latest_deploy.get('version')} introducing the memory regression.",
                        requires_approval=True,
                        command_or_script=f"kubectl rollout undo deployment/{service}",
                    )
                )
            recommendations.append(
                RecommendedRemediation(
                    action="restart",
                    risk_level="Low",
                    description=f"Gracefully restart {service} pods to release accumulated memory buffers.",
                    requires_approval=True,
                    command_or_script=f"kubectl rollout restart deployment/{service}",
                )
            )

        # Hypothesis 3: Deployment Configuration or Regression
        elif has_recent_deploy:
            hypotheses.append(
                RootCauseHypothesis(
                    title="Deployment Regression Introduced in Latest Release",
                    likelihood="High",
                    confidence_score=0.80,
                    rationale=f"Failure signals began immediately following release {latest_deploy.get('version')}. Commits should be inspected for regression.",
                    supporting_evidence_ids=evidence_ids[:3],
                )
            )
            recommendations.append(
                RecommendedRemediation(
                    action="rollback",
                    risk_level="Medium",
                    description=f"Roll back deployment {latest_deploy.get('version')} to restore service stability.",
                    requires_approval=True,
                    command_or_script=f"kubectl rollout undo deployment/{service}",
                )
            )

        # Generic / Downstream Timeout Fallback
        else:
            hypotheses.append(
                RootCauseHypothesis(
                    title="Downstream Dependency Latency Degradation",
                    likelihood="Medium",
                    confidence_score=0.65,
                    rationale=f"Service {service} is experiencing elevated request latency and intermittent errors possibly caused by upstream or downstream network degradation.",
                    supporting_evidence_ids=evidence_ids[:2],
                )
            )
            recommendations.append(
                RecommendedRemediation(
                    action="restart",
                    risk_level="Low",
                    description=f"Restart service pods to reset network connections.",
                    requires_approval=True,
                    command_or_script=f"kubectl rollout restart deployment/{service}",
                )
            )

        # Standard non-destructive remediation: create incident tracking issue
        recommendations.append(
            RecommendedRemediation(
                action="create_jira",
                risk_level="Low",
                description=f"Create post-incident tracking ticket in GitHub/Jira for {service}.",
                requires_approval=False,
                command_or_script=f"gh issue create --title '[Incident] {incident.get('title', 'Outage')}'",
            )
        )

        # Uncertainty factors
        if not deployments:
            uncertainty.append("No recent deployment records found in the preceding 60-minute correlation window.")
        if not hist_incidents:
            uncertainty.append("No exact historical incident matches found for this specific error signature.")
        if not metrics:
            uncertainty.append("Sparse metric telemetry: Database IOPS and CPU profiles were not observed during the event window.")

        top_confidence = hypotheses[0].confidence_score if hypotheses else 0.70
        summary_text = (
            f"{service.replace('-', ' ').title()} is experiencing operational degradation: {incident.get('title', 'outage')}. "
            f"Analysis of {len(evidence_items)} telemetry evidence items indicates {hypotheses[0].title.lower()} as the primary root cause."
        )

        return InvestigationReportOutput(
            summary=summary_text,
            hypotheses=hypotheses,
            supporting_evidence=evidence_items,
            recommendations=recommendations,
            confidence_score=top_confidence,
            uncertainty_factors=uncertainty,
        )


ai_investigation_engine = AIInvestigationEngine()

