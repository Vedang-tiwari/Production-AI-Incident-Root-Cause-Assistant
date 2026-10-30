import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "app_name" in data


@pytest.mark.asyncio
async def test_simulator_and_incidents_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Trigger simulation
        sim_resp = await ac.post(
            "/api/v1/simulator/trigger-scenario",
            json={"scenario": "payment-db-pool-exhaustion", "auto_investigate": True},
        )
        assert sim_resp.status_code == 201
        sim_data = sim_resp.json()
        inc_id = sim_data["incident_id"]
        assert inc_id is not None

        # 2. Get incident details
        inc_resp = await ac.get(f"/api/v1/incidents/{inc_id}")
        assert inc_resp.status_code == 200
        inc_data = inc_resp.json()
        assert inc_data["service"] == "payment-service"

        # 3. Get timeline
        time_resp = await ac.get(f"/api/v1/incidents/{inc_id}/timeline")
        assert time_resp.status_code == 200
        timeline_items = time_resp.json()
        assert len(timeline_items) >= 2

        # 4. Get investigation report
        inv_resp = await ac.get(f"/api/v1/incidents/{inc_id}/investigation")
        assert inv_resp.status_code == 200
        inv_data = inv_resp.json()
        assert len(inv_data["hypotheses"]) > 0

        # 5. List approvals
        appr_resp = await ac.get(f"/api/v1/approvals?incident_id={inc_id}")
        assert appr_resp.status_code == 200
        approvals = appr_resp.json()
        assert len(approvals) > 0
        appr_id = approvals[0]["id"]

        # 6. Take approval action: Approve & Execute
        act_resp = await ac.post(
            f"/api/v1/approvals/{appr_id}/action",
            json={"decision": "approve", "actor": "alice_sre"},
        )
        assert act_resp.status_code == 200
        act_data = act_resp.json()
        assert act_data["status"] == "executed"

        # 7. Verify incident is resolved
        check_resp = await ac.get(f"/api/v1/incidents/{inc_id}")
        assert check_resp.status_code == 200
        assert check_resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_dashboard_html_view():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        assert "Production AI Incident Assistant" in response.text

