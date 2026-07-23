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


async def _create_customer(client, token: str, name: str) -> str:
    resp = await client.post("/api/v1/customers", json={"name": name}, headers=_auth(token))
    return resp.json()["data"]["id"]


async def test_deal_stage_update_recomputes_customer_revenue(client):
    token = await _owner_token(client)
    customer_id = await _create_customer(client, token, "ABC Ltd")

    deal = await client.post(
        f"/api/v1/customers/{customer_id}/deals",
        json={"title": "Renewal", "amount": 100000},
        headers=_auth(token),
    )
    deal_id = deal.json()["data"]["id"]

    fetched = await client.get(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    assert fetched.json()["data"]["revenue_total"] == 100000.0

    won = await client.patch(
        f"/api/v1/customers/{customer_id}/deals/{deal_id}",
        json={"stage": "won"},
        headers=_auth(token),
    )
    assert won.status_code == 200
    assert won.json()["data"]["closed_at"] is not None

    lost = await client.post(
        f"/api/v1/customers/{customer_id}/deals",
        json={"title": "Upsell", "amount": 50000},
        headers=_auth(token),
    )
    lost_id = lost.json()["data"]["id"]
    await client.patch(
        f"/api/v1/customers/{customer_id}/deals/{lost_id}",
        json={"stage": "lost"},
        headers=_auth(token),
    )

    refetched = await client.get(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    # 100000 (won) counted, 50000 (lost) excluded
    assert refetched.json()["data"]["revenue_total"] == 100000.0


async def test_update_deal_not_found(client):
    token = await _owner_token(client)
    customer_id = await _create_customer(client, token, "ABC Ltd")
    resp = await client.patch(
        f"/api/v1/customers/{customer_id}/deals/00000000-0000-0000-0000-000000000000",
        json={"stage": "won"},
        headers=_auth(token),
    )
    assert resp.status_code == 404


async def test_overview_counts_won_revenue_and_at_risk_customers(client):
    token = await _owner_token(client)
    customer_id = await _create_customer(client, token, "ABC Ltd")
    deal = await client.post(
        f"/api/v1/customers/{customer_id}/deals",
        json={"title": "Deal", "amount": 480000},
        headers=_auth(token),
    )
    deal_id = deal.json()["data"]["id"]
    await client.patch(
        f"/api/v1/customers/{customer_id}/deals/{deal_id}", json={"stage": "won"}, headers=_auth(token)
    )

    # A second, stale customer to trigger a real "at risk" flag.
    stale = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    await client.post(
        "/api/v1/customers",
        json={"name": "Stale Co", "last_contact_at": stale},
        headers=_auth(token),
    )

    resp = await client.get("/api/v1/reports/overview", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["total_revenue"] == 480000.0
    assert body["new_deals"] >= 1
    assert body["revenue_at_risk_customer_count"] == 1
    assert "total_revenue" in body["deltas"]


async def test_overview_custom_period_requires_from_and_to(client):
    token = await _owner_token(client)
    resp = await client.get(
        "/api/v1/reports/overview", params={"period": "custom"}, headers=_auth(token)
    )
    assert resp.status_code == 422


async def test_top_customers_ranked_by_revenue(client):
    token = await _owner_token(client)
    low_id = await _create_customer(client, token, "Low Co")
    high_id = await _create_customer(client, token, "High Co")

    for cid, amount in [(low_id, 10000), (high_id, 900000)]:
        deal = await client.post(
            f"/api/v1/customers/{cid}/deals", json={"title": "D", "amount": amount}, headers=_auth(token)
        )
        await client.patch(
            f"/api/v1/customers/{cid}/deals/{deal.json()['data']['id']}",
            json={"stage": "won"},
            headers=_auth(token),
        )

    resp = await client.get("/api/v1/reports/top-customers", headers=_auth(token))
    names = [c["name"] for c in resp.json()["data"]]
    assert names.index("High Co") < names.index("Low Co")


async def test_revenue_by_source_buckets_by_manual_source(client):
    token = await _owner_token(client)
    customer_id = await _create_customer(client, token, "ABC Ltd")
    deal = await client.post(
        f"/api/v1/customers/{customer_id}/deals", json={"title": "D", "amount": 1000}, headers=_auth(token)
    )
    await client.patch(
        f"/api/v1/customers/{customer_id}/deals/{deal.json()['data']['id']}",
        json={"stage": "won"},
        headers=_auth(token),
    )

    resp = await client.get("/api/v1/reports/revenue-by-source", headers=_auth(token))
    assert resp.status_code == 200
    labels = [s["label"] for s in resp.json()["data"]]
    assert "Manually added" in labels


async def test_score_history_defaults_to_organization(client):
    token = await _owner_token(client)
    await _create_customer(client, token, "ABC Ltd")

    resp = await client.get(
        "/api/v1/reports/score-history", params={"entity_type": "organization"}, headers=_auth(token)
    )
    assert resp.status_code == 200


async def test_score_history_requires_entity_id_for_customer(client):
    token = await _owner_token(client)
    resp = await client.get(
        "/api/v1/reports/score-history", params={"entity_type": "customer"}, headers=_auth(token)
    )
    assert resp.status_code == 422
