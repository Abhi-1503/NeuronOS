# NeuronOS API Specification

**Derives from:** MASTER_BLUEPRINT.md Chapter 13, NeuronOS_Database_Spec.md
**Status:** Implementation-ready v1
**Base URL:** `https://api.neuronos.io/api/v1` (placeholder domain)
**Audience:** Frontend + backend engineers, third-party integrators (Phase 4 public API)

---

## 0. Global Conventions

### 0.1 Auth

Every request (except `/auth/login` and `/auth/refresh`) requires:
```
Authorization: Bearer <session_token>
```
The token encodes `user_id` and `organization_id`. `organization_id` is **never** accepted as a request parameter — it is always derived server-side from the token, then set via `SET LOCAL app.current_org_id` for that transaction (enforces the RLS policy in Database Spec §0.1).

### 0.2 Standard Response Envelope

Success:
```json
{
  "data": { ... },
  "meta": { "request_id": "req_9f3a..." }
}
```

List endpoints add pagination:
```json
{
  "data": [ ... ],
  "meta": {
    "request_id": "req_9f3a...",
    "pagination": { "cursor": "eyJpZCI6Ii4uLiJ9", "has_more": true, "limit": 25 }
  }
}
```

### 0.3 Standard Error Envelope

```json
{
  "error": {
    "code": "validation_error",
    "message": "deadline must be a valid ISO 8601 date",
    "details": { "field": "deadline" }
  },
  "meta": { "request_id": "req_9f3a..." }
}
```

Standard `error.code` values used across all endpoints: `validation_error` (422), `not_found` (404), `permission_denied` (403), `unauthenticated` (401), `rate_limited` (429), `conflict` (409), `integration_error` (502), `internal_error` (500).

### 0.4 Pagination

Cursor-based, not offset-based (offset pagination degrades on large, frequently-changing tables like `timeline_events`). Query params: `?cursor=...&limit=25` (max `limit` = 100).

### 0.5 Idempotency (required on any endpoint with an external side effect)

**Gap addressed:** a retried request (network retry, double-clicked button, replayed background job) could otherwise cause the same email to send twice or the same record to be created twice — and unlike most write operations, these cannot be undone after the fact.

Every endpoint that triggers an irreversible external effect — `POST /ai-actions/{id}/approve`, `POST /meetings/{id}/summarize`, `POST /automations/{id}/dry-run`, `POST /documents` — **requires** an `Idempotency-Key` header:

```
Idempotency-Key: <client-generated UUID, stable across retries of the same logical request>
```

Server behavior: on first receipt of a given key for a given endpoint + organization, the request executes normally and the key is stored (backed by the `idempotency_key` columns on `ai_action_executions` / `automation_runs` — see Database Spec §7.4). On any subsequent request with the same key, the server returns the **original** response without re-executing the side effect (`200`/`201` with the original body, not a `409` — a safe retry should look like success to the client, not like an error). Keys are considered stale and eligible for garbage collection after 24 hours.

The frontend is responsible for generating a fresh key per *logical* user action (e.g., one click of "Approve") and reusing that same key if it needs to retry that specific action after a network failure — generating a new key on retry defeats the purpose entirely.

**Note on `POST /documents` specifically (flagged during verification):** the idempotency key protects against a retried upload request creating a duplicate embedding/processing job, but it does not by itself catch a user manually re-uploading the same file twice as two separate logical actions (two different idempotency keys, same content). Recommend also computing a content hash (e.g., SHA-256) of the uploaded file and treating a hash match within the same organization as a likely duplicate — surfaced to the user as "This looks like a file you already uploaded — replace it, or upload as new?" rather than silently processing (and paying to embed) the same document twice.

### 0.6 Rate Limits

| Endpoint category | Limit |
|---|---|
| Read endpoints (GET) | 300 requests/min per organization |
| Write endpoints (POST/PATCH/DELETE) | 100 requests/min per organization |
| AI-generation endpoints (chat, summarize, draft) | 20 requests/min per organization — these are the expensive ones |

Rate limit headers returned on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

### 0.7 Permissions Shorthand

Used in every endpoint table below: **Owner**, **Admin**, **Member**, **Any** (any authenticated org member). Where an endpoint's access additionally depends on record-level scope (e.g., a Member only seeing their assigned projects), it's noted explicitly.

---

## 1. Auth

### `POST /auth/login`
- **Purpose:** Authenticate a user, issue a session token.
- **Body:** `{ "email": string, "password": string }`
- **Validation:** email format; password non-empty.
- **Response 200:** `{ "data": { "token": string, "user": {...}, "organization": {...} } }`
- **Errors:** `401 unauthenticated` (bad credentials), `403 permission_denied` (suspended user).
- **Permissions:** none (public endpoint).
- **Rate limit:** 10/min per IP (stricter than default — brute-force protection).

### `POST /auth/logout`
- **Purpose:** Invalidate the current session token.
- **Response 204:** empty body.
- **Permissions:** Any.

### `POST /auth/invite`
- **Purpose:** Invite a new user to the organization.
- **Body:** `{ "email": string, "role": "admin"|"member" }`
- **Validation:** role cannot be `owner` (ownership transfer is a separate, explicit flow).
- **Response 201:** `{ "data": { "invitation_id": string, "email": string, "status": "invited" } }`
- **Permissions:** Owner, Admin.

### `POST /auth/refresh`
- **Purpose:** Exchange a refresh token for a new session token.
- **Body:** `{ "refresh_token": string }`
- **Response 200:** `{ "data": { "token": string } }`

---

## 2. Customers

### `GET /customers`
- **Query params:** `status`, `sort` (`relationship_score`, `last_contact_at`), `cursor`, `limit`.
- **Response 200:** paginated list of customer summaries (id, name, status, relationship_score, revenue_total, last_contact_at, next_action).
- **Permissions:** Any (visibility may be scoped by org policy — Phase 3+).

### `POST /customers`
- **Body:** `{ "name": string, "owner_user_id"?: uuid, "status"?: string }`
- **Validation:** `name` required, 1–200 chars.
- **Response 201:** full customer object.
- **Permissions:** Any (Member can create; visibility of others' customers may still be scoped).

### `GET /customers/{id}`
- **Response 200:** full customer object including computed `relationship_score`, `ai_summary` (latest cached AI Summary), and `recommended_next_action` (latest linked, unactioned AI Action if any).
- **Errors:** `404 not_found`.
- **Permissions:** Any.

### `PATCH /customers/{id}`
- **Body:** any subset of mutable fields (`name`, `status`, `owner_user_id`).
- **Response 200:** updated customer object.
- **Permissions:** Any (record owner), Admin, Owner.

### `DELETE /customers/{id}`
- **Behavior:** soft delete (`deleted_at` set); cascades soft-delete intent to timeline events/deals is **not** automatic — those remain queryable via the customer's `deleted_at` recovery window.
- **Response 204.**
- **Permissions:** Admin, Owner.

### `GET /customers/{id}/timeline`
- **Query params:** `event_type`, `cursor`, `limit`.
- **Response 200:** paginated timeline events, newest first.
- **Permissions:** Any.

### `POST /customers/{id}/timeline`
- **Purpose:** manually add a timeline entry (e.g., a note).
- **Body:** `{ "event_type": "note", "title": string, "body"?: string, "occurred_at"?: ISO8601 }`
- **Response 201:** the created timeline event.
- **Permissions:** Any.

### `GET /customers/{id}/deals`
- **Response 200:** list of deals for this customer.
- **Permissions:** Any.

### `POST /customers/{id}/deals`
- **Body:** `{ "title": string, "stage"?: string, "amount": number, "currency"?: string, "expected_close_date"?: date }`
- **Validation:** `amount > 0`.
- **Response 201:** created deal.
- **Permissions:** Any.

---

## 3. Projects

### `GET /projects`
- **Query params:** `status`, `customer_id`, `assignee_id`, `cursor`, `limit`.
- **Response 200:** paginated list (id, name, status, progress_pct, deadline, member avatars, open risk_flag count).
- **Permissions:** Any — **but** a Member only sees projects they're a `project_member` of unless org policy grants broader visibility (Blueprint §17.1).

### `POST /projects`
- **Body:** `{ "name": string, "customer_id"?: uuid, "deadline"?: date, "member_user_ids"?: uuid[] }`
- **Response 201:** created project, with `project_members` rows created for any `member_user_ids`.
- **Permissions:** Any.

### `GET /projects/{id}`
- **Response 200:** full project object including `risk_flags` (unresolved only, unless `?include_resolved=true`), `members`, task counts by status.
- **Permissions:** Any assigned member, Admin, Owner.

### `PATCH /projects/{id}`
- **Body:** any subset of `name`, `status`, `progress_pct`, `deadline`.
- **Validation:** `progress_pct` 0–100; setting `status` to `completed` auto-sets `completed_at`.
- **Response 200:** updated project.
- **Permissions:** project lead (`project_members.role_on_project = 'lead'`), Admin, Owner.

### `POST /projects/{id}/members`
- **Body:** `{ "user_id": uuid, "role_on_project"?: string }`
- **Response 201:** created membership.
- **Permissions:** project lead, Admin, Owner.

### `GET /projects/{id}/tasks`
- **Query params:** `status`, `assignee_id`.
- **Response 200:** list of tasks.
- **Permissions:** any project member.

### `POST /projects/{id}/tasks`
- **Body:** `{ "title": string, "assignee_id"?: uuid, "due_date"?: date }`
- **Response 201:** created task (`source = 'manual'`).
- **Permissions:** any project member.

### `PATCH /projects/{id}/tasks/{task_id}`
- **Body:** any subset of `title`, `status`, `assignee_id`, `due_date`.
- **Response 200:** updated task.
- **Permissions:** any project member (assignee or lead in stricter org policies — Phase 3+ configurable).

### `GET /projects/{id}/risk-flags`
- **Response 200:** list of risk flags (resolved and unresolved, with a filter param), each including `reasoning` and `confidence_score` (Database Spec §3.4) — same rendering requirement as AI Actions: the reasoning is shown next to the flag, not hidden behind a click, per the trust-calibration fix in Master Blueprint §2.7.
- **Permissions:** any project member.

### `POST /projects/{id}/risk-flags/{flag_id}/resolve`
- **Response 200:** updated risk flag with `resolved_at` set.
- **Permissions:** project lead, Admin, Owner.

---

## 4. Meetings

### `GET /meetings`
- **Query params:** `status` (`upcoming`,`brief_ready`,`completed`,`needs_notes`), `customer_id`, `from`, `to`, `cursor`, `limit`.
- **Response 200:** paginated list matching the Meetings screen's Today/Upcoming/Past/Needs Notes tabs.
- **Permissions:** Any (attendee-scoped for Members in stricter org policies).

### `POST /meetings`
- **Body:** `{ "title": string, "customer_id"?: uuid, "scheduled_at": ISO8601, "duration_minutes"?: int, "platform"?: string, "attendee_user_ids"?: uuid[], "attendee_contacts"?: [{ "name": string, "email": string }] }`
- **Response 201:** created meeting.
- **Permissions:** Any.

### `GET /meetings/{id}`
- **Response 200:** full meeting object, attendees, summary (if generated), action items.
- **Permissions:** attendee, Admin, Owner.

### `GET /meetings/{id}/brief`
- **Purpose:** returns the AI-generated pre-meeting brief (talking points, outstanding items, related customer/project context).
- **Behavior:** if no brief exists yet, triggers synchronous generation (Action Engine) if the meeting is within a configurable window (e.g., next 24h), otherwise `202 Accepted` with a job reference for async generation.
- **Response 200:** `{ "data": { "summary": string, "talking_points": string[], "related_context": {...} } }`
- **Permissions:** attendee, Admin, Owner.
- **Rate limit:** counts against the AI-generation limit (§0.6).

### `POST /meetings/{id}/summarize`
- **Purpose:** trigger post-meeting summarization from notes/transcript.
- **Body:** `{ "transcript"?: string, "notes"?: string }` — at least one required.
- **Behavior:** async job; response returns immediately with job status, summary delivered via webhook/notification when ready.
- **Response 202:** `{ "data": { "job_id": string, "status": "processing" } }`
- **Permissions:** attendee, Admin, Owner.
- **Rate limit:** AI-generation limit.

### `GET /meetings/{id}/action-items`
- **Response 200:** list of extracted action items, each with `task_id` if promoted.
- **Permissions:** attendee, Admin, Owner.

### `POST /meetings/{id}/action-items/{item_id}/promote`
- **Purpose:** convert a meeting action item into a real Task in a project.
- **Body:** `{ "project_id": uuid, "assignee_id"?: uuid, "due_date"?: date }`
- **Response 201:** the created Task; the action item is updated with `task_id`.
- **Permissions:** attendee, Admin, Owner.

---

## 5. Documents / Knowledge

### `POST /documents`
- **Purpose:** upload a new document.
- **Body:** multipart/form-data — `file`, `title`?, `visibility`?.
- **Validation:** file type in allowed set (pdf, docx, pptx, xlsx); max size (e.g., 50MB, confirm against R2 plan limits).
- **Behavior:** file stored in R2, `documents` row created synchronously, chunking + embedding + AI summary generation happen async (Knowledge Engine job).
- **Response 202:** `{ "data": { "document_id": uuid, "status": "processing" } }`
- **Permissions:** Any (subject to `visibility` rules on read).

### `GET /documents/{id}`
- **Response 200:** document metadata, `ai_summary`, `tags`, `linked_entities`.
- **Errors:** `403 permission_denied` if `visibility = 'admin_only'` and requester is a Member.
- **Permissions:** scoped by `visibility`.

### `GET /documents/search`
- **Purpose:** semantic + keyword search across the knowledge base.
- **Query params:** `q` (required), `file_type`, `limit`.
- **Behavior:** hybrid search — keyword match on `documents.title` + vector similarity on `document_chunks.embedding` for `q`, merged and ranked.
- **Response 200:** ranked list of documents with matching chunk excerpts.
- **Permissions:** Any (results filtered by `visibility`).
- **Rate limit:** AI-generation limit (embedding the query counts as generation-adjacent).

### `DELETE /documents/{id}`
- **Behavior:** soft delete; underlying R2 object retained until hard-delete job runs (30-day window).
- **Response 204.**
- **Permissions:** uploader, Admin, Owner.

---

## 5A. Linked Entities (Context Corrections)

**Gap addressed:** the Context Engine's `linked_entities` table had a `confidence` field for AI-inferred links but no endpoint existed for a user to confirm or correct one — meaning a document mis-linked to the wrong customer would silently feed wrong context into the Decision and Action Engines with no way to fix it (Strategic Gap Analysis §3.3).

### `GET /linked-entities/review-queue`
- **Purpose:** surface AI-suggested links that most need a human look — low-confidence (`status = 'ai_suggested'` and `confidence` below a configurable threshold, default 0.7) links, newest first.
- **Query params:** `entity_type` (filter to review links involving a specific type, e.g. `customer`), `cursor`, `limit`.
- **Response 200:** paginated list, each item showing both sides of the link (e.g., "Document: 'Q3 Proposal.pdf' ↔ Customer: 'XYZ Solutions'") and the `confidence` score.
- **Permissions:** Any (visibility scoped to what the requester can already see on both linked entities).

### `POST /linked-entities/{id}/confirm`
- **Purpose:** a user confirms an AI-suggested link is correct.
- **Behavior:** `status` → `confirmed`, `corrected_by_user_id`/`corrected_at` set (Database Spec §5.4). A confirmed link is weighted normally by downstream engines from this point on.
- **Response 200:** updated linked entity record.
- **Permissions:** Any (with edit access to at least one side of the link).

### `POST /linked-entities/{id}/reject`
- **Purpose:** a user flags an AI-suggested link as wrong.
- **Body:** `{ "correct_target_type"?: string, "correct_target_id"?: uuid }` — optional: if the user knows the correct link, this creates a new `manual`-status linked entity in the same request rather than requiring a separate follow-up call.
- **Behavior:** `status` → `rejected` on the original row (retained, not deleted, so the Context Engine has a negative-example signal for the Learning Engine); if `correct_target_*` is provided, a new row is created with `status = 'manual'`.
- **Response 200:** `{ "data": { "rejected": {...}, "created"?: {...} } }`
- **Permissions:** Any (with edit access to at least one side of the link).

### `POST /documents/{id}/links`
- **Purpose:** manually link a document to a customer/project/meeting (covers the case where a user wants to create a link the Context Engine hasn't inferred at all, not just correct a wrong one).
- **Body:** `{ "target_type": string, "target_id": uuid, "relationship"?: string }`
- **Response 201:** created linked entity, `status = 'manual'`.
- **Permissions:** Any (with edit access to the document).

---

## 5B. Onboarding

**Gap addressed:** there was no endpoint support for the cold-start onboarding flow described in `NeuronOS_Onboarding_Spec.md` — a brand-new organization with zero data has nothing for Pulse or the AI Workspace to work with, and there was no way to track which first-run path a user took or when they reached a real first insight.

### `GET /onboarding/status`
- **Purpose:** returns the current org's onboarding state — which path (if any) has been started, completion status of each step in that path, and whether the "first insight" milestone has been reached.
- **Response 200:** `{ "data": { "onboarding_method": string|null, "steps": [{ "key": string, "label": string, "completed": bool }], "first_insight_at": ISO8601|null } }`
- **Permissions:** Any.

### `POST /onboarding/select-method`
- **Purpose:** records which first-run path the user is starting (connect an integration / upload documents / add top customers manually — see Onboarding Spec §2).
- **Body:** `{ "method": "integration"|"documents"|"manual_customers" }`
- **Response 200:** updated onboarding status.
- **Permissions:** Admin, Owner (the person doing initial setup).

### `POST /onboarding/complete`
- **Purpose:** marks onboarding as complete once the org has enough data for a real insight (checked server-side against the actual data — e.g., ≥1 customer with a timeline event, or ≥1 connected integration with a completed initial sync — not just a user clicking "done").
- **Behavior:** sets `organizations.onboarding_completed_at`; if this is also the first time any real insight has been generated for this org, also sets `onboarding_first_insight_at`.
- **Response 200:** updated onboarding status.
- **Permissions:** Admin, Owner.

---

## 6. AI Workspace (Chat)

### `POST /chat/messages`
- **Purpose:** send a message to the AI Workspace; the core RAG + reasoning endpoint.
- **Body:** `{ "conversation_id"?: uuid, "message": string }` — omitting `conversation_id` starts a new conversation.
- **Behavior:** retrieves relevant context (Knowledge Engine RAG + Context Engine relationship graph scoped to what the requesting user can see), generates a response with the Action/Decision engines as needed, returns with source citations.
- **Response 200:** `{ "data": { "conversation_id": uuid, "message": { "role": "assistant", "content": string, "citations": [{ "type": "document"|"customer"|"project", "id": uuid, "excerpt": string }] } } }`
- **Permissions:** Any — response content must never leak data outside the requesting user's visibility scope (Blueprint §5.3 — this is a hard requirement, tested explicitly, not assumed from RAG source filtering alone).
- **Rate limit:** AI-generation limit.

### `GET /chat/conversations`
- **Response 200:** list of the requesting user's past conversations (id, title/summary, updated_at).
- **Permissions:** Any (own conversations only).

### `GET /chat/conversations/{id}`
- **Response 200:** full message history for a conversation.
- **Permissions:** conversation owner only.

---

## 7. AI Actions

### `GET /ai-actions`
- **Query params:** `status` (`suggested`,`approved`,`rejected`,`delegated`,`executed`), `assigned_to_me` (bool), `priority`, `severity_tier`, `cursor`, `limit`.
- **Response 200:** paginated queue matching the AI Actions screen's Suggested/All/Completed/Delegated tabs. Each item includes `reasoning`, `confidence_score`, `severity_tier`, and `is_reversible` (Database Spec §7.1) — **the frontend must render `reasoning` visibly alongside the conclusion, not behind an optional "why?" expander**, per the trust-calibration fix in Master Blueprint §2.7. This is a product requirement, not just a field being available.
- **Permissions:** Any (scoped to `assigned_to_user_id` unless Admin/Owner viewing org-wide).

### `GET /ai-actions/{id}`
- **Response 200:** full action detail including `related_entity` expanded (e.g., the customer it's about), plus `reasoning`, `confidence_score`, `severity_tier`, `is_reversible`.
- **Permissions:** assignee, delegate, Admin, Owner.

### `POST /ai-actions/{id}/approve`
- **Purpose:** approve and trigger execution.
- **Headers:** `Idempotency-Key` (required — see §0.5).
- **Body:** `{ "edited_content"?: object, "confirm_high_severity"?: boolean }` — `edited_content` is optional edits to the AI-drafted content before execution (e.g., editing a drafted email body), recorded as a diff for the Learning Engine. **`confirm_high_severity` is required and must be `true` when `severity_tier = 'high'`** (Database Spec §7.1) — this is the schema-backed implementation of "irreversible, high-stakes actions get visibly higher-friction confirmation" (Strategic Gap Analysis §3.4). The frontend should surface this as an explicit secondary confirmation step (e.g., "This will send a real invoice to ABC Ltd for ₹4,80,000 — Confirm Send"), not a silent boolean flip.
- **Validation:** `422 validation_error` if `severity_tier = 'high'` and `confirm_high_severity` is missing or `false`.
- **Behavior:** status → `approved` synchronously, execution enqueued async, `decided_by_user_id`/`decided_at` set. If this action originated from an automation in `graduating` mode (`ai_actions.related_entity_type = 'automation'`), approval also increments that automation's `approved_run_count` (Database Spec §6.1) and, once its `graduation_threshold` is reached, promotes the automation to `live` mode automatically — surfaced to the user as a notification ("Follow-up reminder automation is now fully automated after 5 approved runs"), not a silent background change.
- **Response 200:** updated AI Action (status `approved`, execution pending).
- **Errors:** `409 conflict` if the action is not in `suggested` state (e.g., already approved by someone else).
- **Permissions:** assignee, delegate, Admin, Owner.

### `POST /ai-actions/{id}/reject`
- **Body:** `{ "reason"?: string }` — optional, feeds Learning Engine.
- **Behavior:** if this action originated from an automation in `graduating` mode, rejection resets that automation's `approved_run_count` to 0 (Database Spec §6.1) — a rejection is treated as a signal the automation's logic needs revisiting, not just a delay to graduation.
- **Response 200:** updated AI Action (status `rejected`).
- **Permissions:** assignee, delegate, Admin, Owner.

### `POST /ai-actions/{id}/delegate`
- **Body:** `{ "delegated_to_user_id": uuid }`
- **Response 200:** updated AI Action (status `delegated`).
- **Permissions:** assignee, Admin, Owner.

---

## 8. Automations

### `GET /automations`
- **Response 200:** list with cached stats (`times_triggered`, `success_rate_pct`).
- **Permissions:** Any (read), — configuration is Admin+.

### `POST /automations`
- **Body:** `{ "name": string, "trigger_type": string, "trigger_config": object, "action_type": string, "action_config": object, "is_active"?: bool }`
- **Validation:** `trigger_config`/`action_config` shape validated against a per-`trigger_type`/`action_type` JSON schema (not free-form).
- **Response 201:** created automation.
- **Permissions:** Admin, Owner.

### `PATCH /automations/{id}`
- **Body:** any subset of mutable fields, commonly `{ "is_active": bool }` to toggle.
- **Response 200:** updated automation.
- **Permissions:** Admin, Owner.

### `POST /automations/{id}/promote-mode`
- **Purpose:** explicitly move an automation between `mode` states (Database Spec §6.1) — e.g., an Admin manually forcing a `graduating` automation back to `dry_run`, or manually promoting to `live` before the graduation threshold is reached (an explicit override, logged as such).
- **Body:** `{ "mode": "dry_run"|"graduating"|"live"|"paused", "reason"?: string }`
- **Validation:** any manual promotion to `live` bypassing the graduation threshold requires `reason` to be non-empty (forces a deliberate decision to be recorded, not a casual click).
- **Response 200:** updated automation.
- **Permissions:** Admin, Owner.

### `GET /automations/{id}/dry-run-results`
- **Purpose:** view what a `dry_run`-mode automation *would have* done — the simulated `automation_runs` rows (status `simulated`), each showing the target entity and the action content that would have executed.
- **Query params:** `cursor`, `limit`.
- **Response 200:** paginated list of simulated runs with full preview content (e.g., the exact email that would have been sent, and to whom).
- **Permissions:** Admin, Owner.

### `GET /automations/{id}/runs`
- **Response 200:** paginated run history (for the "Triggered 48 times, Success 96%" stat drill-down).
- **Permissions:** Admin, Owner.

---

## 9. Reports

### `GET /reports/overview`
- **Query params:** `period` (`this_month`,`last_month`,`custom`), `from`, `to` (for custom).
- **Response 200:** `{ "data": { "total_revenue": number, "new_deals": int, "revenue_at_risk": number, "open_invoices": number, "deltas": {...} } }`
- **Permissions:** Any.

### `GET /reports/revenue-trend`
- **Response 200:** time series for the Revenue Trend chart (this month vs. last month overlay).
- **Permissions:** Any.

### `GET /reports/revenue-by-source`
- **Response 200:** breakdown (existing clients / new clients / referrals / others) for the donut chart.
- **Permissions:** Any.

### `GET /reports/top-customers`
- **Query params:** `limit` (default 10).
- **Response 200:** ranked list (customer, revenue, deals, relationship_score) for the Top Performing Customers table.
- **Permissions:** Any.

### `GET /reports/score-history`
- **Purpose:** **fixes a real gap found during verification** — `score_history` (Database Spec §7.5) was added to support score trend charts and algorithm-version tracking, but no endpoint existed to actually retrieve it, meaning the table was unreachable from the product surface entirely.
- **Query params:** `entity_type` (`organization`|`customer`, required), `entity_id` (required unless `entity_type=organization`, in which case it defaults to the requesting org), `from`, `to`.
- **Response 200:** `{ "data": [{ "score": int, "algorithm_version": string, "computed_at": ISO8601 }, ...] }` — ordered by `computed_at` ascending, ready to plot directly.
- **Behavior:** any point in the returned series where `algorithm_version` differs from the previous point should be visually marked by the frontend (Blueprint §12.5) — this endpoint returns the raw version-tagged data; the annotation is a rendering responsibility, not something this endpoint pre-computes.
- **Permissions:** Any (for `organization` scope); any (for `customer` scope, subject to normal customer visibility rules).

---

## 10. Integrations

**Provider list (updated):** Gmail, Google Drive, Google Calendar, **Outlook, Microsoft 365 (Calendar + Mail via Microsoft Graph)**, Slack, WhatsApp Business, HubSpot, Salesforce, Zoho CRM, Zoho Books, QuickBooks. See Master Blueprint §9.1 for the review-process reality behind each of these — they are not equal-effort to add, and the review clock for each should start well before the integration's code is complete.

### `GET /integrations`
- **Response 200:** list of available providers with connection status for this org (connected/not connected/sync_error), plus, per provider: `provider_review_status` (Database Spec §8.1 — `not_submitted`/`in_review`/`approved`/`rejected`, NeuronOS's own standing with that provider, not the org's connection) and `last_synced_at`/staleness info (Database Spec §7.6) so the frontend can render a "data as of X hours ago" caveat consistent with what Pulse shows.
- **Permissions:** Any (read); connect/disconnect is Admin+.

### `POST /integrations/{provider}/connect`
- **Purpose:** initiate OAuth flow.
- **Response 200:** `{ "data": { "oauth_url": string } }` — frontend redirects the user here; the provider callback is a separate, provider-specific endpoint not listed individually here (e.g., `GET /integrations/gmail/callback`).
- **Permissions:** Admin, Owner.

### `DELETE /integrations/{provider}`
- **Behavior:** revokes tokens with the provider, soft-deletes the `integration_connections` row, does **not** delete already-synced data (documents, timeline events already ingested remain, tagged with `source_integration_id` for traceability).
- **Response 204.**
- **Permissions:** Admin, Owner.

### `GET /integrations/{provider}/sync-status`
- **Response 200:** `{ "data": { "status": string, "last_synced_at": ISO8601, "last_sync_error"?: string } }`
- **Permissions:** Admin, Owner.

---

## 11. Settings

### `GET /organization`
- **Response 200:** organization profile (name, industry, size, timezone, plan, business_health_score, `terms_accepted_version`, `terms_accepted_at`, `dpa_signed_at`).
- **Permissions:** Any (read).

### `PATCH /organization`
- **Body:** any subset of mutable profile fields.
- **Permissions:** Admin, Owner.

### `GET /organization/members`
- **Response 200:** list of users in the org (name, email, role, status, last_login_at).
- **Permissions:** Any.

### `PATCH /organization/members/{user_id}`
- **Body:** `{ "role"?: string, "status"?: string }`
- **Validation:** cannot set `role: owner` here (separate transfer flow); cannot suspend the sole Owner.
- **Permissions:** Admin (role changes among non-owners), Owner (all changes).

### `POST /organization/accept-terms`
- **Purpose:** **fixes a real gap found during verification** — `organizations.terms_accepted_version`/`terms_accepted_at` (Database Spec §1.1) were added to support the liability/ToS posture (Blueprint §17.8), but no endpoint existed to actually record acceptance, meaning the fields were unreachable from signup or any other flow.
- **Body:** `{ "version": string }` — the ToS version identifier being accepted (matches whatever versioning scheme the actual Terms of Service document uses).
- **Behavior:** sets `terms_accepted_version`/`terms_accepted_at`. Called as part of the signup flow (blocking — an org's Owner cannot proceed past signup without accepting) and again whenever a materially changed ToS version is published (non-blocking for existing usage, but surfaced prominently until accepted).
- **Response 200:** updated organization profile.
- **Permissions:** Owner only (the Terms are accepted on behalf of the organization by its Owner).

### `POST /organization/request-dpa`
- **Purpose:** closes the same kind of gap as above for `dpa_signed_at` — a business wanting a Data Processing Agreement had a schema field to eventually hold the signed date, but no way to actually request one.
- **Body:** `{ "requested_by_email"?: string, "notes"?: string }`
- **Behavior:** MVP implementation can be as simple as creating an internal notification/ticket for the team to follow up with the standard DPA template (`NeuronOS_Trust_Security_FAQ.md` §4) — this does not need to be a self-serve e-signature flow at launch. `dpa_signed_at` is set manually by an admin once the agreement is actually executed, not by this endpoint itself.
- **Response 202:** `{ "data": { "status": "request_received" } }`
- **Permissions:** Admin, Owner.

### `DELETE /organization` (Danger Zone — Delete Account)
- **Behavior:** requires a confirmation token issued by a prior `POST /organization/request-deletion` step (two-step to prevent accidental single-request deletion); hard-deletes the organization and cascades per Database Spec §1.1.
- **Permissions:** Owner only.

---

## 12. Webhooks (outbound, Phase 2+)

For async operations (`meetings/{id}/summarize`, `documents` processing, `ai-actions` execution), NeuronOS delivers a webhook rather than requiring polling:

```json
POST <org's configured webhook URL>
{
  "event": "meeting.summarized",
  "organization_id": "...",
  "data": { "meeting_id": "...", "summary": {...} },
  "sent_at": "2026-07-18T10:00:00Z"
}
```

Signed with an HMAC header (`X-NeuronOS-Signature`) so receivers can verify authenticity. Full event catalog (`document.processed`, `ai_action.executed`, `automation.failed`, etc.) is a follow-on deliverable once Phase 2 webhook infrastructure is scoped.

---

## 13. Versioning & Deprecation Policy

- Breaking changes require a new version prefix (`/api/v2/`), not in-place changes to `/v1/`.
- Deprecated endpoints return a `Deprecation` header with a sunset date at least 90 days out before removal (relevant once external/Phase 4 API consumers exist; internally the frontend can move faster by agreement between teams).

---

## 14. Open Items Carried Into Implementation

1. File size/type limits for `POST /documents` need confirming against actual R2 plan and expected document types before launch.
2. The exact shape of `trigger_config`/`action_config` JSON schemas per automation type (§8) needs to be finalized with frontend before the automation builder UI (Phase 2) is built against it.
3. Webhook event catalog (§12) is scoped for Phase 2 but not yet fully enumerated — track separately.
4. Whether `GET /chat/messages` responses should stream (SSE) rather than return a single blocking response is a UX decision that affects this spec — recommend streaming for perceived latency, to be confirmed with frontend before implementation.
5. **[Resolved this pass]** No idempotency guarantee on side-effecting endpoints — see §0.5 (`Idempotency-Key` header, now required on approve/summarize/dry-run/upload endpoints).
6. **[Resolved this pass]** Automations shipped with no dry-run or graduated-autonomy path, contradicting the approve-first philosophy — see the new `POST /automations/{id}/promote-mode` and `GET /automations/{id}/dry-run-results` endpoints, and the updated behavior on `/ai-actions/{id}/approve` and `/reject`.
7. **[Resolved this pass]** Missing Outlook/Microsoft 365 integration and no way to expose provider review status or data staleness to the frontend — see §10.
8. **New open item:** `POST /automations/{id}/promote-mode`'s manual-override path (forcing `live` before the graduation threshold) needs a UI decision on how prominently to surface that this bypasses the normal trust-building path — a buried setting invites accidental misuse of exactly the override meant to be deliberate.
9. **[Resolved this pass]** No visible reasoning/confidence on AI-generated risk flags or actions, risking a "cried wolf" trust collapse — see the updated `GET /ai-actions`, `GET /ai-actions/{id}`, and `GET /projects/{id}/risk-flags` responses (§7, §3), which now include `reasoning`/`confidence_score` with an explicit rendering requirement.
10. **[Resolved this pass]** No correction loop for AI-inferred document/entity links — see the new §5A (`GET /linked-entities/review-queue`, `POST /linked-entities/{id}/confirm`/`reject`).
11. **[Resolved this pass]** Irreversibility wasn't gated by severity in the approve flow — see the updated `POST /ai-actions/{id}/approve` (§7), which now requires `confirm_high_severity` for `severity_tier = 'high'` actions.
12. **[Resolved this pass]** No endpoint support for cold-start onboarding — see the new §5B (`GET /onboarding/status`, `POST /onboarding/select-method`, `POST /onboarding/complete`).
13. **New open item:** the exact threshold for what counts as "enough data for a real insight" in `POST /onboarding/complete`'s server-side check needs to be defined precisely (e.g., is one customer with one timeline event enough, or does Pulse need at least a handful of entities to produce a non-trivial Business Health score?) — this is a product decision that should be made with real early-user data, not guessed once and left unexamined.
14. **[Resolved during verification pass]** `score_history` (Database Spec §7.5) had no retrieval endpoint at all — added `GET /reports/score-history`.
15. **[Resolved during verification pass]** `organizations.terms_accepted_version`/`dpa_signed_at` had no endpoint to actually set them — added `POST /organization/accept-terms` and `POST /organization/request-dpa`.
16. **[Resolved during verification pass]** `POST /documents`'s idempotency handling didn't address duplicate uploads of the same file as two separate logical actions — added a content-hash dedup recommendation (§0.5).
