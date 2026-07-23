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


async def test_send_message_starts_a_new_conversation(client):
    token = await _owner_token(client)
    resp = await client.post(
        "/api/v1/chat/messages", json={"message": "What's up with my customers?"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["conversation_id"]
    assert body["message"]["role"] == "assistant"
    # No ANTHROPIC_API_KEY in the test environment — must be the honest fallback,
    # not a fabricated "AI" answer.
    assert "ANTHROPIC_API_KEY" in body["message"]["content"]


async def test_second_message_reuses_conversation_id(client):
    token = await _owner_token(client)
    first = await client.post(
        "/api/v1/chat/messages", json={"message": "Hello"}, headers=_auth(token)
    )
    conversation_id = first.json()["data"]["conversation_id"]

    second = await client.post(
        "/api/v1/chat/messages",
        json={"conversation_id": conversation_id, "message": "Follow-up question"},
        headers=_auth(token),
    )
    assert second.status_code == 200
    assert second.json()["data"]["conversation_id"] == conversation_id


async def test_chat_cites_a_matching_document_and_customer(client):
    token = await _owner_token(client)
    await client.post("/api/v1/customers", json={"name": "XYZ Solutions"}, headers=_auth(token))
    await client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"XYZ Solutions renewal is due next month.", "text/plain")},
        headers=_auth(token),
    )

    resp = await client.post(
        "/api/v1/chat/messages",
        json={"message": "Tell me about XYZ Solutions renewal"},
        headers=_auth(token),
    )
    citations = resp.json()["data"]["message"]["citations"]
    types = {c["type"] for c in citations}
    assert "document" in types
    assert "customer" in types


async def test_list_and_get_conversation(client):
    token = await _owner_token(client)
    sent = await client.post(
        "/api/v1/chat/messages", json={"message": "Hello there"}, headers=_auth(token)
    )
    conversation_id = sent.json()["data"]["conversation_id"]

    listed = await client.get("/api/v1/chat/conversations", headers=_auth(token))
    assert listed.status_code == 200
    assert any(c["id"] == conversation_id for c in listed.json()["data"])

    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=_auth(token))
    assert detail.status_code == 200
    messages = detail.json()["data"]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Hello there"


async def test_get_unknown_conversation_404(client):
    token = await _owner_token(client)
    resp = await client.get(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000", headers=_auth(token)
    )
    assert resp.status_code == 404


async def test_cannot_send_message_to_someone_elses_conversation(client):
    owner_token = await _owner_token(client, email="owner-a@acme-fixture.com")
    sent = await client.post(
        "/api/v1/chat/messages", json={"message": "Private thought"}, headers=_auth(owner_token)
    )
    conversation_id = sent.json()["data"]["conversation_id"]

    other_signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Other Org",
            "name": "Other Owner",
            "email": "owner-b@other-fixture.com",
            "password": "hunter22",
        },
    )
    other_token = other_signup.json()["data"]["token"]

    resp = await client.post(
        "/api/v1/chat/messages",
        json={"conversation_id": conversation_id, "message": "Trying to hijack"},
        headers=_auth(other_token),
    )
    assert resp.status_code in (403, 404)
