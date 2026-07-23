import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.db import get_db_session
from app.models.ai_action import AIAction
from tests.conftest import drive_session

pytestmark = pytest.mark.asyncio


async def _owner_token_and_org(client, *, email="owner@acme-fixture.com"):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Acme Inc",
            "name": "Jane Owner",
            "email": email,
            "password": "hunter22",
        },
    )
    data = resp.json()["data"]
    return data["token"], data["organization"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_stale_customer_with_action(client, token: str) -> str:
    stale = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    resp = await client.post(
        "/api/v1/customers",
        json={"name": "Stale Co", "last_contact_at": stale},
        headers=_auth(token),
    )
    return resp.json()["data"]["recommended_next_action"]["id"]


async def _insert_high_severity_action(organization_id: str) -> str:
    """No endpoint generates a `high`-severity action yet in this slice (Decision Engine
    v1 only produces `send_followup_email`, severity `low`) — inserted directly to test
    the severity-gating path against a real high-severity `action_type_registry` entry."""
    async with drive_session(get_db_session(organization_id=organization_id)) as session:
        action = AIAction(
            organization_id=uuid.UUID(organization_id),
            title="Send invoice to PQR Technologies",
            description="Invoice for ₹82,000",
            action_type="generate_invoice",
            severity_tier="high",
            is_reversible=False,
            reasoning="Contract milestone reached; invoice is ready to send.",
            confidence_score=0.9,
            priority="high",
            status="suggested",
            generated_by_engine="test_fixture",
        )
        session.add(action)
        await session.flush()
        action_id = action.id
    return str(action_id)


async def test_list_and_get_action(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)

    listed = await client.get("/api/v1/ai-actions", headers=_auth(token))
    assert listed.status_code == 200
    assert any(a["id"] == action_id for a in listed.json()["data"])

    fetched = await client.get(f"/api/v1/ai-actions/{action_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["reasoning"] is not None


async def test_approve_low_severity_action(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)

    resp = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "executed"
    assert body["decided_at"] is not None
    assert body["executed_at"] is not None


async def test_approve_requires_idempotency_key_header(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)

    resp = await client.post(f"/api/v1/ai-actions/{action_id}/approve", json={}, headers=_auth(token))
    assert resp.status_code == 422


async def test_approving_twice_with_same_idempotency_key_does_not_re_execute(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)
    key = str(uuid.uuid4())

    first = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": key},
    )
    second = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": key},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["executed_at"] == second.json()["data"]["executed_at"]


async def test_approving_an_already_executed_action_with_a_new_key_conflicts(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)

    await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    again = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "conflict"


async def test_high_severity_action_requires_explicit_confirmation(client):
    token, organization_id = await _owner_token_and_org(client)
    action_id = await _insert_high_severity_action(organization_id)

    without_confirm = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert without_confirm.status_code == 422
    assert without_confirm.json()["error"]["code"] == "validation_error"

    with_confirm = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={"confirm_high_severity": True},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert with_confirm.status_code == 200
    assert with_confirm.json()["data"]["status"] == "executed"


async def test_reject_action(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)

    resp = await client.post(
        f"/api/v1/ai-actions/{action_id}/reject", json={"reason": "Not relevant"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "rejected"


async def test_cannot_approve_a_rejected_action(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)
    await client.post(f"/api/v1/ai-actions/{action_id}/reject", json={}, headers=_auth(token))

    resp = await client.post(
        f"/api/v1/ai-actions/{action_id}/approve",
        json={},
        headers={**_auth(token), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 409


async def test_delegate_action(client):
    token, _ = await _owner_token_and_org(client)
    action_id = await _create_stale_customer_with_action(client, token)

    invite = await client.post(
        "/api/v1/auth/invite",
        json={"email": "teammate@acme-fixture.com", "role": "member"},
        headers=_auth(token),
    )
    invitation_id = invite.json()["data"]["invitation_id"]

    resp = await client.post(
        f"/api/v1/ai-actions/{action_id}/delegate",
        json={"delegated_to_user_id": invitation_id},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "delegated"
    assert resp.json()["data"]["delegated_to_user_id"] == invitation_id
