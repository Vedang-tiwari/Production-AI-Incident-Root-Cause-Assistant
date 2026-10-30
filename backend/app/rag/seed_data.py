from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.logging import logger
from backend.app.db.models import HistoricalIncident, Runbook
from backend.app.db.repositories import KnowledgeRepository
from backend.app.rag.embeddings import embedding_generator
from backend.app.rag.vector_store import vector_store

DEFAULT_RUNBOOKS = [
    {
        "id": "RB-DB-001",
        "title": "Database Connection Pool Exhaustion Troubleshooting",
        "service": "all",
        "category": "database",
        "tags": ["database", "postgres", "pool", "timeout", "connections"],
        "content_markdown": """# Runbook: Database Connection Pool Exhaustion

## Symptoms
- Application logs showing `Database connection timeout`, `HikariPool - Connection is not available`, or `OperationalError: connection pool exhausted`.
- HTTP 500 or 504 errors across user-facing endpoints.
- DB Connection Pool utilization metric > 90%.

## Diagnostic Steps
1. Verify active connection count using `pg_stat_activity` or connection pool metrics.
2. Check recent deployments for unclosed database connections or missing connection context managers.
3. Check for slow-running queries holding connections open (`SELECT * FROM pg_stat_activity WHERE state = 'active'`).
4. Inspect traffic spikes or cascading retries saturating the pool.

## Remediation Actions
1. **Immediate Mitigation:** Increase connection pool size by 25-50% if database host has adequate RAM/CPU.
2. **If post-deployment:** Immediately roll back recent deployment if connection leaks were introduced.
3. **Restart Service Pods:** Gracefully restart affected service pods to drain leaked orphaned connections.
""",
    },
    {
        "id": "RB-MEM-002",
        "title": "Memory Leak and High Heap Usage Remediation",
        "service": "all",
        "category": "infrastructure",
        "tags": ["memory", "oom", "crashloop", "heap", "leak"],
        "content_markdown": """# Runbook: High Memory Usage & OOM Kills

## Symptoms
- Pod status `OOMKilled` or exit code 137.
- Memory utilization metric steadily climbing above 90% without returning to baseline.
- Significant increase in response latency due to excessive GC (Garbage Collection) pauses.

## Diagnostic Steps
1. Compare memory trajectory before and after the most recent deployment version.
2. Inspect cache retention policies (unbounded in-memory LRU or dictionary growth).
3. Review heap dumps or memory profiling logs for retaining objects.

## Remediation Actions
1. **Immediate Mitigation:** Trigger rolling restart of application instances.
2. **Rollback:** Roll back to the previous stable release tag if memory climbed immediately after a deploy.
3. **Scale Resource Limits:** Temporarily scale pod memory limits by 1.5x to prevent cascading crashes while debugging.
""",
    },
    {
        "id": "RB-DEP-003",
        "title": "Deployment Regression & Automated Rollback Guide",
        "service": "all",
        "category": "deployment",
        "tags": ["deployment", "regression", "rollback", "release", "canary"],
        "content_markdown": """# Runbook: Deployment Regression & Fast Rollback

## Symptoms
- Error rate or response latency sharply rises within 10 minutes of a new deployment.
- New exception signatures appearing in error tracking immediately following release.
- Health checks or readiness probes failing on newly deployed revisions.

## Diagnostic Steps
1. Check CI/CD deployment timeline and identify exact commit SHA and release tag.
2. Inspect git diff of the deployment for database schema changes, configuration mistakes, or missing environment variables.
3. Determine if rollback requires database migration reversion.

## Remediation Actions
1. **Execute Rollback:** Issue rollback command `kubectl rollout undo deployment/<service>` or trigger CI/CD rollback pipeline.
2. **Notify Team:** Announce rollback in `#incidents` Slack channel.
3. **Lock Pipeline:** Block further deployments to the service until post-mortem review is completed.
""",
    },
    {
        "id": "RB-API-004",
        "title": "Cascading Microservice Timeout and Circuit Breaker Tripping",
        "service": "all",
        "category": "network",
        "tags": ["timeout", "circuit-breaker", "cascading-failure", "downstream", "http-504"],
        "content_markdown": """# Runbook: Downstream Dependency Failure & Circuit Breakers

## Symptoms
- HTTP 504 Gateway Timeout or HTTP 502 Bad Gateway reported by upstream services.
- Circuit breaker state transitioned to OPEN.
- Thread or connection pool starvation across caller microservices.

## Diagnostic Steps
1. Inspect distributed traces to isolate the exact downstream dependency returning timeouts.
2. Verify downstream service health, external third-party API status, or cloud provider degradation.
3. Check timeout and retry configurations: excessive retries without exponential backoff cause self-inflicted DDoS.

## Remediation Actions
1. **Enable Fallback:** Trip circuit breaker manually to return cached or degraded response immediately.
2. **Adjust Timeouts:** Lower client timeout thresholds to fail fast and free up worker threads.
3. **Throttle Ingress Traffic:** Apply rate limiting on public API gateway for failing endpoints.
""",
    },
]

DEFAULT_HISTORICAL_INCIDENTS = [
    {
        "id": "INC-HIST-101",
        "title": "Payment Service HikariCP Database Connection Pool Depletion",
        "service": "payment-service",
        "root_cause": "Database connection pool exhaustion caused by an unclosed connection in the new audit logger transaction block introduced in v2.4.0.",
        "resolution": "Rolled back v2.4.0, increased pool size from 10 to 30, and patched the database connection context manager to guarantee connection release.",
        "error_signatures": [
            "Database connection timeout",
            "HikariPool-1 - Connection is not available",
            "HTTP 500 Internal Server Error",
        ],
        "resolved_at": datetime.now(timezone.utc) - timedelta(days=14),
    },
    {
        "id": "INC-HIST-102",
        "title": "Order Processing Service OOM Crash following v2.3.1 Deployment",
        "service": "order-service",
        "root_cause": "Memory leak caused by an unbounded in-memory cache accumulating order validation tokens without an expiration TTL.",
        "resolution": "Rolled back deployment v2.3.1 to v2.3.0. Added Redis TTL for token caching and configured heap memory limits with prometheus alert.",
        "error_signatures": [
            "java.lang.OutOfMemoryError: Java heap space",
            "Pod terminated: OOMKilled",
            "Exit code 137",
        ],
        "resolved_at": datetime.now(timezone.utc) - timedelta(days=30),
    },
    {
        "id": "INC-HIST-103",
        "title": "Checkout Service Downstream Gateway Timeout",
        "service": "checkout-service",
        "root_cause": "Third-party payment gateway experienced latency spike of 8000ms. Checkout service worker threads blocked waiting for responses without adequate read timeouts.",
        "resolution": "Reduced HTTP read timeout from 30s to 3s and activated circuit breaker with graceful error response to customers.",
        "error_signatures": [
            "HTTP 504 Gateway Timeout",
            "ReadTimeoutError",
            "Thread pool exhausted",
        ],
        "resolved_at": datetime.now(timezone.utc) - timedelta(days=45),
    },
]


async def seed_knowledge_base(db: AsyncSession) -> None:
    """Populates both the SQL database and vector store with default runbooks and historical incidents."""
    repo = KnowledgeRepository(db)

    # 1. Seed Runbooks
    for rb_data in DEFAULT_RUNBOOKS:
        vec = embedding_generator.generate_embedding(
            f"{rb_data['title']}\n{' '.join(rb_data['tags'])}\n{rb_data['content_markdown']}"
        )
        rb = Runbook(
            id=rb_data["id"],
            title=rb_data["title"],
            service=rb_data["service"],
            category=rb_data["category"],
            tags=rb_data["tags"],
            content_markdown=rb_data["content_markdown"],
            embedding_vector=vec,
        )
        await repo.add_runbook(rb)
        vector_store.add_document(
            collection="runbooks",
            doc_id=rb.id,
            content=f"{rb.title}\n{rb.content_markdown}",
            metadata={
                "id": rb.id,
                "title": rb.title,
                "service": rb.service,
                "category": rb.category,
                "tags": rb.tags,
            },
            vector=vec,
        )

    # 2. Seed Historical Incidents
    for hi_data in DEFAULT_HISTORICAL_INCIDENTS:
        text_for_vec = (
            f"{hi_data['title']} {hi_data['service']} {hi_data['root_cause']} "
            f"{' '.join(hi_data['error_signatures'])}"
        )
        vec = embedding_generator.generate_embedding(text_for_vec)
        hi = HistoricalIncident(
            id=hi_data["id"],
            title=hi_data["title"],
            service=hi_data["service"],
            root_cause=hi_data["root_cause"],
            resolution=hi_data["resolution"],
            error_signatures=hi_data["error_signatures"],
            resolved_at=hi_data["resolved_at"],
            embedding_vector=vec,
        )
        await repo.add_historical_incident(hi)
        vector_store.add_document(
            collection="historical_incidents",
            doc_id=hi.id,
            content=f"{hi.title}\nRoot Cause: {hi.root_cause}\nResolution: {hi.resolution}\nSignatures: {' '.join(hi.error_signatures)}",
            metadata={
                "id": hi.id,
                "title": hi.title,
                "service": hi.service,
                "root_cause": hi.root_cause,
                "resolution": hi.resolution,
                "error_signatures": hi.error_signatures,
            },
            vector=vec,
        )

    logger.info(
        f"Knowledge base seeded with {len(DEFAULT_RUNBOOKS)} runbooks and {len(DEFAULT_HISTORICAL_INCIDENTS)} historical incidents."
    )

