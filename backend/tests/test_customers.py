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


async def test_create_customer_recent_contact_has_no_recommended_action(client):
    token = await _owner_token(client)
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = await client.post(
        "/api/v1/customers",
        json={"name": "ABC Ltd", "last_contact_at": recent},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["name"] == "ABC Ltd"
    assert body["relationship_score"] > 90
    assert body["recommended_next_action"] is None


async def test_create_customer_stale_contact_generates_recommended_action(client):
    token = await _owner_token(client)
    stale = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    resp = await client.post(
        "/api/v1/customers",
        json={"name": "Stale Co", "last_contact_at": stale},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    action = body["recommended_next_action"]
    assert action is not None
    assert action["severity_tier"] == "low"
    assert action["reasoning"] is not None
    assert "14 day" in action["reasoning"]
    assert action["confidence_score"] is not None


async def test_create_customer_with_no_last_contact_at_still_scores(client):
    token = await _owner_token(client)
    resp = await client.post(
        "/api/v1/customers", json={"name": "Brand New Co"}, headers=_auth(token)
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["last_contact_at"] is None
    assert body["relationship_score"] is not None


async def test_list_and_get_customer(client):
    token = await _owner_token(client)
    created = await client.post(
        "/api/v1/customers", json={"name": "ABC Ltd"}, headers=_auth(token)
    )
    customer_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/customers", headers=_auth(token))
    assert listed.status_code == 200
    assert any(c["id"] == customer_id for c in listed.json()["data"])

    fetched = await client.get(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["name"] == "ABC Ltd"


async def test_get_unknown_customer_404(client):
    token = await _owner_token(client)
    resp = await client.get(
        "/api/v1/customers/00000000-0000-0000-0000-000000000000", headers=_auth(token)
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_adding_recent_timeline_event_clears_the_flag(client):
    token = await _owner_token(client)
    stale = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    created = await client.post(
        "/api/v1/customers",
        json={"name": "Was Stale Co", "last_contact_at": stale},
        headers=_auth(token),
    )
    customer_id = created.json()["data"]["id"]
    assert created.json()["data"]["recommended_next_action"] is not None

    await client.post(
        f"/api/v1/customers/{customer_id}/timeline",
        json={"event_type": "email", "title": "Sent a check-in email"},
        headers=_auth(token),
    )

    refetched = await client.get(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    body = refetched.json()["data"]
    assert body["relationship_score"] > 90
    assert body["recommended_next_action"] is None


async def test_add_and_list_deals(client):
    token = await _owner_token(client)
    created = await client.post(
        "/api/v1/customers", json={"name": "ABC Ltd"}, headers=_auth(token)
    )
    customer_id = created.json()["data"]["id"]

    deal = await client.post(
        f"/api/v1/customers/{customer_id}/deals",
        json={"title": "Renewal", "amount": 480000, "currency": "INR"},
        headers=_auth(token),
    )
    assert deal.status_code == 201
    assert deal.json()["data"]["amount"] == 480000.0

    deals = await client.get(f"/api/v1/customers/{customer_id}/deals", headers=_auth(token))
    assert len(deals.json()["data"]) == 1


async def test_delete_customer_requires_admin_or_owner(client):
    token = await _owner_token(client)
    created = await client.post(
        "/api/v1/customers", json={"name": "ABC Ltd"}, headers=_auth(token)
    )
    customer_id = created.json()["data"]["id"]

    deleted = await client.delete(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    assert deleted.status_code == 204

    gone = await client.get(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    assert gone.status_code == 404


async def test_customers_are_isolated_across_organizations(client):
    token_a = await _owner_token(client, email="a@orga-fixture.com")
    token_b = await _owner_token(client, email="b@orgb-fixture.com")

    await client.post("/api/v1/customers", json={"name": "Org A Customer"}, headers=_auth(token_a))

    list_b = await client.get("/api/v1/customers", headers=_auth(token_b))
    assert list_b.json()["data"] == []
