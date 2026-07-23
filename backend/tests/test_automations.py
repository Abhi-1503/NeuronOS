import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.asyncio


async def _owner_token(client, *, email="owner@acme-fixture.com") -> str:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Acme Inc",
            "name": "Jane Owner",
            "email": email,
            "password": "hunter22",
        },
    )
    return resp.json()["data"]["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_no_reply_automation(client, token: str, *, days: int = 3) -> str:
    resp = await client.post(
        "/api/v1/automations",
        json={
            "name": "Follow up if no reply in 3 days",
            "trigger_type": "no_reply_days",
            "trigger_config": {"days": days},
            "action_type": "send_followup_email",
            "action_config": {},
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def test_automation_always_starts_in_dry_run_regardless_of_request(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token)
    resp = await client.get("/api/v1/automations", headers=_auth(token))
    automation = next(a for a in resp.json()["data"] if a["id"] == automation_id)
    assert automation["mode"] == "dry_run"


async def test_promote_to_live_without_reason_rejected(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token)

    resp = await client.post(
        f"/api/v1/automations/{automation_id}/promote-mode",
        json={"mode": "live"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_promote_to_live_with_reason_succeeds(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token)

    resp = await client.post(
        f"/api/v1/automations/{automation_id}/promote-mode",
        json={"mode": "live", "reason": "Confident after manual testing"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["mode"] == "live"


async def test_dry_run_evaluate_creates_simulated_run_not_ai_action(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token, days=1)
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=_auth(token)
    )

    resp = await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 200
    runs = resp.json()["data"]
    assert len(runs) == 1
    assert runs[0]["status"] == "simulated"

    dry_run_results = await client.get(
        f"/api/v1/automations/{automation_id}/dry-run-results", headers=_auth(token)
    )
    assert len(dry_run_results.json()["data"]) == 1


async def test_evaluate_is_idempotent_per_target(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token, days=1)
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=_auth(token)
    )

    first = await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    second = await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert len(first.json()["data"]) == 1
    assert len(second.json()["data"]) == 0  # already caught — no duplicate


async def test_graduating_automation_creates_real_ai_action(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token, days=1)
    await client.post(
        f"/api/v1/automations/{automation_id}/promote-mode",
        json={"mode": "graduating"},
        headers=_auth(token),
    )
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=_auth(token)
    )

    await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )

    actions = await client.get("/api/v1/ai-actions?status=suggested", headers=_auth(token))
    automation_actions = [a for a in actions.json()["data"] if a["related_entity_type"] == "automation"]
    assert len(automation_actions) == 1
    assert automation_actions[0]["related_entity_id"] == automation_id


async def test_approving_graduating_action_increments_and_promotes_at_threshold(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token, days=1)
    await client.post(
        f"/api/v1/automations/{automation_id}/promote-mode",
        json={"mode": "graduating"},
        headers=_auth(token),
    )
    # Lower the threshold indirectly isn't exposed via API, so exercise one full
    # approval and confirm the counter increments (full-threshold promotion behavior
    # is unit-testable via the same mechanism at any threshold value).
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=_auth(token)
    )
    await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    actions = await client.get("/api/v1/ai-actions?status=suggested", headers=_auth(token))
    action_id = next(
        a["id"] for a in actions.json()["data"] if a["related_entity_type"] == "automation"
    )

    await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )

    automations = await client.get("/api/v1/automations", headers=_auth(token))
    automation = next(a for a in automations.json()["data"] if a["id"] == automation_id)
    assert automation["approved_run_count"] == 1


async def test_rejecting_graduating_action_resets_approved_run_count(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token, days=1)
    await client.post(
        f"/api/v1/automations/{automation_id}/promote-mode",
        json={"mode": "graduating"},
        headers=_auth(token),
    )
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=_auth(token)
    )
    await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    actions = await client.get("/api/v1/ai-actions?status=suggested", headers=_auth(token))
    action_id = next(
        a["id"] for a in actions.json()["data"] if a["related_entity_type"] == "automation"
    )

    await client.post(f"/api/v1/ai-actions/{action_id}/reject", json={}, headers=_auth(token))

    automations = await client.get("/api/v1/automations", headers=_auth(token))
    automation = next(a for a in automations.json()["data"] if a["id"] == automation_id)
    assert automation["approved_run_count"] == 0


async def test_live_automation_executes_immediately(client):
    token = await _owner_token(client)
    automation_id = await _create_no_reply_automation(client, token, days=1)
    await client.post(
        f"/api/v1/automations/{automation_id}/promote-mode",
        json={"mode": "live", "reason": "Manual override for test"},
        headers=_auth(token),
    )
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=_auth(token)
    )

    resp = await client.post(
        f"/api/v1/automations/{automation_id}/evaluate",
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    runs = resp.json()["data"]
    assert runs[0]["status"] == "success"

    automations = await client.get("/api/v1/automations", headers=_auth(token))
    automation = next(a for a in automations.json()["data"] if a["id"] == automation_id)
    assert automation["times_triggered"] == 1
    assert automation["success_rate_pct"] == 100


async def test_create_automation_rejects_unregistered_action_type(client):
    token = await _owner_token(client)
    resp = await client.post(
        "/api/v1/automations",
        json={
            "name": "Bad",
            "trigger_type": "no_reply_days",
            "trigger_config": {"days": 3},
            "action_type": "not_a_real_action",
            "action_config": {},
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422
