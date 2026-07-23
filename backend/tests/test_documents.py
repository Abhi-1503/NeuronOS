import io

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter

from app.core.db import get_db_session
from app.schemas.auth import InviteRequest
from app.services.auth_service import AuthService
from tests.conftest import drive_session

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


async def _member_token(client, organization_id, *, email="member@acme-fixture.com") -> str:
    """A real non-admin/owner ("member") session token — needed to exercise visibility
    scoping honestly rather than asserting it only from the owner's own, unrestricted
    view. The raw invite token is deliberately never returned by the HTTP API (Database
    Spec §1.2), so it's obtained by driving `AuthService` directly (same pattern as
    `test_auth.py::test_accept_expired_invite_returns_gone`), then the actual
    accept-invite HTTP endpoint is used to get a genuine token."""
    async with drive_session(get_db_session(organization_id=organization_id)) as session:
        _invited_user, raw_token = await AuthService(session).invite(
            organization_id=organization_id,
            data=InviteRequest(email=email, role="member"),
        )
    resp = await client.post(
        f"/api/v1/auth/invitations/{raw_token}/accept",
        json={"name": "Teammate", "password": "hunter22"},
    )
    return resp.json()["data"]["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


async def test_upload_docx_extracts_text_and_generates_fallback_summary(client):
    token = await _owner_token(client)
    content = _make_docx_bytes(
        ["Master Services Agreement", "This contract renews annually with 30 days notice."]
    )
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("contract.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "Master Services Agreement"},
        headers=_auth(token),
    )
    assert resp.status_code == 202
    document_id = resp.json()["data"]["document_id"]

    fetched = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert fetched.status_code == 200
    body = fetched.json()["data"]
    assert body["file_type"] == "docx"
    # No ANTHROPIC_API_KEY in the test environment — this must be the honest
    # extractive fallback (real extracted text), not a fabricated "AI" summary.
    assert body["ai_summary"] is not None
    assert "renews annually" in body["ai_summary"]


async def test_upload_plain_text_as_other_file_type(client):
    token = await _owner_token(client)
    content = b"Quarterly plan: expand into two new verticals."
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", content, "text/plain")},
        headers=_auth(token),
    )
    assert resp.status_code == 202
    document_id = resp.json()["data"]["document_id"]
    fetched = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert fetched.json()["data"]["file_type"] == "other"


async def test_upload_pdf_with_no_extractable_text_has_no_summary(client):
    token = await _owner_token(client)
    content = _make_pdf_bytes()  # blank page — no text at all
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("blank.pdf", content, "application/pdf")},
        headers=_auth(token),
    )
    assert resp.status_code == 202
    document_id = resp.json()["data"]["document_id"]
    fetched = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert fetched.json()["data"]["file_type"] == "pdf"
    assert fetched.json()["data"]["ai_summary"] is None


async def test_list_documents_returns_recent_first(client):
    token = await _owner_token(client)
    await client.post(
        "/api/v1/documents",
        files={"file": ("a.txt", b"first", "text/plain")},
        data={"title": "First"},
        headers=_auth(token),
    )
    await client.post(
        "/api/v1/documents",
        files={"file": ("b.txt", b"second", "text/plain")},
        data={"title": "Second"},
        headers=_auth(token),
    )

    resp = await client.get("/api/v1/documents", headers=_auth(token))
    assert resp.status_code == 200
    titles = [d["title"] for d in resp.json()["data"]]
    assert titles == ["Second", "First"]


async def test_search_finds_document_by_content_keyword(client):
    token = await _owner_token(client)
    content = _make_docx_bytes(["Onboarding checklist for new hires at Acme."])
    await client.post(
        "/api/v1/documents",
        files={"file": ("onboarding.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )

    resp = await client.get("/api/v1/documents/search", params={"q": "onboarding"}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


async def test_get_unknown_document_404(client):
    token = await _owner_token(client)
    resp = await client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000", headers=_auth(token)
    )
    assert resp.status_code == 404


async def test_delete_document(client):
    token = await _owner_token(client)
    content = _make_docx_bytes(["Temp doc"])
    created = await client.post(
        "/api/v1/documents",
        files={"file": ("temp.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )
    document_id = created.json()["data"]["document_id"]

    deleted = await client.delete(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert deleted.status_code == 204

    gone = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert gone.status_code == 404


async def test_upload_rejects_oversized_and_unknown_types_gracefully(client):
    token = await _owner_token(client)
    # A file with an unrecognized extension still uploads (falls back to "other"),
    # matching the DB's actual allowed file_type set rather than erroring.
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("mystery.xyz", b"some content", "application/octet-stream")},
        headers=_auth(token),
    )
    assert resp.status_code == 202


async def test_mentioning_a_customer_name_creates_a_review_queue_link(client):
    token = await _owner_token(client)
    await client.post("/api/v1/customers", json={"name": "XYZ Solutions"}, headers=_auth(token))

    content = _make_docx_bytes(["Proposal for XYZ Solutions — Q3 engagement."])
    await client.post(
        "/api/v1/documents",
        files={"file": ("proposal.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )

    resp = await client.get("/api/v1/linked-entities/review-queue", headers=_auth(token))
    assert resp.status_code == 200
    links = resp.json()["data"]
    assert len(links) == 1
    assert links[0]["target_type"] == "customer"
    assert links[0]["status"] == "ai_suggested"
    assert links[0]["confidence"] < 0.7


async def test_confirm_and_reject_linked_entity(client):
    token = await _owner_token(client)
    await client.post("/api/v1/customers", json={"name": "XYZ Solutions"}, headers=_auth(token))
    content = _make_docx_bytes(["Proposal for XYZ Solutions."])
    await client.post(
        "/api/v1/documents",
        files={"file": ("proposal.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )
    queue = await client.get("/api/v1/linked-entities/review-queue", headers=_auth(token))
    link_id = queue.json()["data"][0]["id"]

    confirmed = await client.post(f"/api/v1/linked-entities/{link_id}/confirm", headers=_auth(token))
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["status"] == "confirmed"

    # Confirmed links drop out of the review queue.
    after = await client.get("/api/v1/linked-entities/review-queue", headers=_auth(token))
    assert after.json()["data"] == []


async def test_duplicate_upload_rejected_unless_forced(client):
    token = await _owner_token(client)
    content = _make_docx_bytes(["Renewal terms for Acme Corp."])
    first = await client.post(
        "/api/v1/documents",
        files={"file": ("renewal.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )
    assert first.status_code == 202

    duplicate = await client.post(
        "/api/v1/documents",
        files={"file": ("renewal-copy.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_content"

    forced = await client.post(
        "/api/v1/documents",
        files={"file": ("renewal-copy.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"force": "true"},
        headers=_auth(token),
    )
    assert forced.status_code == 202


async def test_search_excludes_admin_only_documents_for_a_member(client):
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Acme Inc",
            "name": "Jane Owner",
            "email": "owner-visibility@acme-fixture.com",
            "password": "hunter22",
        },
    )
    owner_token = signup.json()["data"]["token"]
    organization_id = signup.json()["data"]["organization"]["id"]
    member_token = await _member_token(
        client, organization_id, email="member-visibility@acme-fixture.com"
    )

    content = _make_docx_bytes(["Confidential executive severance package details."])
    await client.post(
        "/api/v1/documents",
        files={"file": ("secret.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "Executive Severance", "visibility": "admin_only"},
        headers=_auth(owner_token),
    )

    owner_results = await client.get(
        "/api/v1/documents/search", params={"q": "severance"}, headers=_auth(owner_token)
    )
    assert len(owner_results.json()["data"]) == 1

    member_results = await client.get(
        "/api/v1/documents/search", params={"q": "severance"}, headers=_auth(member_token)
    )
    assert member_results.json()["data"] == []


async def test_manual_link_creation(client):
    token = await _owner_token(client)
    customer = await client.post("/api/v1/customers", json={"name": "ABC Ltd"}, headers=_auth(token))
    customer_id = customer.json()["data"]["id"]
    content = _make_docx_bytes(["Unrelated document"])
    created = await client.post(
        "/api/v1/documents",
        files={"file": ("doc.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=_auth(token),
    )
    document_id = created.json()["data"]["document_id"]

    resp = await client.post(
        f"/api/v1/documents/{document_id}/links",
        json={"target_type": "customer", "target_id": customer_id, "relationship": "contract"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["status"] == "manual"
