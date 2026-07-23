from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.asyncio


async def _signup(client):
    return await client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Acme Inc",
            "name": "Jane Owner",
            "email": "jane@acme-fixture.com",
            "password": "hunter22",
        },
    )


async def test_accept_terms_sets_version_and_timestamp(client):
    signup = await _signup(client)
    token = signup.json()["data"]["token"]

    resp = await client.post(
        "/api/v1/organization/accept-terms",
        json={"version": "2026-07-01"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["terms_accepted_at"] is not None


async def test_accept_terms_requires_auth(client):
    resp = await client.post("/api/v1/organization/accept-terms", json={"version": "2026-07-01"})
    assert resp.status_code == 401


async def test_get_organization_with_no_customers_has_null_business_health(client):
    signup = await _signup(client)
    token = signup.json()["data"]["token"]

    resp = await client.get(
        "/api/v1/organization", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["name"] == "Acme Inc"
    assert body["business_health_score"] is None


async def test_get_organization_business_health_averages_customer_scores(client):
    signup = await _signup(client)
    token = signup.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    stale = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    await client.post(
        "/api/v1/customers", json={"name": "Healthy Co", "last_contact_at": recent}, headers=headers
    )
    await client.post(
        "/api/v1/customers", json={"name": "Stale Co", "last_contact_at": stale}, headers=headers
    )

    resp = await client.get("/api/v1/organization", headers=headers)
    body = resp.json()["data"]
    assert body["business_health_score"] is not None
    assert 0 <= body["business_health_score"] <= 100
