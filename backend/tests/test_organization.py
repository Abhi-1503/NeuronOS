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
