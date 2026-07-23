# NeuronOS Database Specification

**Derives from:** MASTER_BLUEPRINT.md, Chapter 12
**Status:** Implementation-ready v1 — covers all MVP + Phase 2 entities
**Engine:** PostgreSQL 16+ with `pgvector` extension
**Audience:** Backend engineers, DBAs, migration authors

---

## 0. Conventions Used Throughout

- All primary keys: `UUID DEFAULT gen_random_uuid()`.
- Every tenant-scoped table includes `organization_id UUID NOT NULL REFERENCES organizations(id)` and it is **always** the leading column in composite indexes.
- Every table includes the audit quad: `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (maintained via trigger, not application code — see §0.3), `created_by UUID REFERENCES users(id)`, `deleted_at TIMESTAMPTZ NULL` (soft delete).
- Enum-like fields use Postgres `CHECK` constraints on `TEXT` rather than native `ENUM` types, so adding a new status value is a simple migration, not a type-alter.
- Money fields stored as `NUMERIC(14,2)` with an explicit `currency CHAR(3)` column (default `'INR'`) — never `FLOAT`.
- Foreign keys default to `ON DELETE RESTRICT` unless a table is a true child of its parent (e.g., `tasks` under `projects`), in which case `ON DELETE CASCADE` is used — each table below states which applies.

### 0.1 Row-Level Security (RLS)

RLS is enabled on every tenant-scoped table. Standard policy pattern:

```sql
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON customers
  USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);
```

**Three corrections made during Phase 0 implementation, all caught only by a test that actually exercises RLS across two organizations with a pooled connection — not by inspection:**

1. **`current_setting`'s second argument (`missing_ok = true`) is required, not optional.** Without it, `current_setting('app.current_org_id')` *raises* `unrecognized configuration parameter` in any session where that setting was never touched at all (e.g. the pre-authentication `auth_service_bypass` path on `users`, §0.1 addendum, which sets `app.bypass_rls_for_auth` but never `app.current_org_id`) — since permissive policies on the same table are evaluated together, that one unset variable was enough to break every query against `users`. `missing_ok = true` makes it return `NULL` instead of erroring in that case.
2. **`NULLIF(..., '')` is required around the `missing_ok`-guarded call, not just the flag itself.** Under connection pooling, a physical connection that has *previously* held a transaction-local (`set_config(..., true)`) value for a custom setting reverts to an empty string `''` — not `NULL` — once that transaction ends, if the setting was never given a plain session-level value. A later request reusing that same pooled connection without setting `app.current_org_id` in its own transaction would otherwise try to cast `''::uuid`, which errors, rather than correctly evaluating to "no match." `NULLIF` normalizes both the never-set (`NULL`) and previously-set-then-reverted (`''`) cases to `NULL` before the cast.
3. **`ENABLE ROW LEVEL SECURITY` alone is not sufficient — `FORCE ROW LEVEL SECURITY` is required too.** Postgres exempts a table's *owner* (and superusers, unconditionally) from RLS policies by default, even with RLS enabled. Since the role that runs migrations necessarily owns every table it creates, an application that connects using that same role would have RLS silently do nothing — no error, no warning, just full visibility across every organization. `FORCE ROW LEVEL SECURITY` closes this for the owner (not for superusers — see the role separation below, which is the actual fix; FORCE is defense-in-depth on top of it). **This is precisely why the application must never connect using the migration/owner role** — see the new `neuronos_app` role below.

### 0.1.1 Application Database Role

**Gap surfaced during Phase 0 implementation:** the original schema had one implicit Postgres role in mind for everything — whichever role ran the migrations. RLS being a no-op against that same role wasn't a hypothetical risk; it's exactly what happened the first time the RLS cross-tenant test actually ran; the query returned every organization's rows with no error of any kind.

**Resolution:** two distinct roles, never interchangeable:

| Role | Used by | Privileges |
|---|---|---|
| Migration/owner role (e.g. `neuronos`) | Alembic only | Owns every table; DDL rights |
| `neuronos_app` | The running application (every request) | `SELECT/INSERT/UPDATE/DELETE` on all tables (granted explicitly, plus `ALTER DEFAULT PRIVILEGES` so future migrations' new tables are covered automatically); explicitly `NOSUPERUSER NOBYPASSRLS`; **no DDL rights, no table ownership** |

The application's connection string (`DATABASE_URL`) must always point at `neuronos_app`, never at the owner role — this is the actual enforcement mechanism, with `FORCE ROW LEVEL SECURITY` above as a second, redundant layer. The role and its grants are created by the first migration (so they exist from Phase 0 onward). Its password is read from the `NEURONOS_APP_ROLE_PASSWORD` environment variable **at the moment the role is first created** (falling back to a local-dev placeholder only when that variable is unset) — every real environment sets this from its own secrets mechanism before running the migration there for the first time, rather than needing a manual `ALTER ROLE` follow-up step. This is deliberately a create-time read only, not re-applied on every subsequent migration run: doing so unconditionally would mean a migration run with the variable accidentally unset (e.g. a misconfigured CI job) silently resets an already-rotated production password back to the placeholder. Rotating the password on an already-created role is a separate, deliberate `ALTER ROLE neuronos_app WITH PASSWORD '...'` action, not an automatic side effect of re-running migrations.

The application sets `app.current_org_id` at the start of every request (via `SET LOCAL` inside the transaction), derived from the authenticated token — never from a client-supplied parameter. This is a defense-in-depth layer underneath the ORM-level scoping already enforced in the service layer (Blueprint §17.2) — a bug in application code cannot leak cross-tenant data because the database itself refuses it.

**Decision record — connection pooling mode (resolved this pass, do not silently revisit):** `SET LOCAL` scopes its setting to the current transaction on whatever physical connection is executing it. A pooler running in **transaction-mode pooling** (e.g., PgBouncer's default, or Railway's managed Postgres proxy in its default configuration) can hand that same physical connection to a *different* request's transaction the moment the first transaction commits — meaning a stale `app.current_org_id` from a previous tenant's request could theoretically still be set if any code path ever reads it outside the exact transaction that issued the `SET LOCAL`, or if a connection is reused before the setting is properly reset. This is exactly the kind of failure mode that passes in testing (low concurrency, one org at a time) and only surfaces under real concurrent multi-tenant load — at which point it's a cross-tenant data leak, not a bug report.

NeuronOS therefore runs its database connections in **session-mode pooling**, not transaction-mode: each request/service-layer session holds a dedicated connection for the lifetime of that session, and `app.current_org_id` is set once per request against a connection that isn't handed to a different request mid-flight. This trades a small amount of connection-count efficiency (session-mode pools support fewer concurrent clients per pool than transaction-mode for the same connection budget) for eliminating an entire class of tenant-isolation bug at the infrastructure layer, which is the correct trade at NeuronOS's current scale. **This is a deliberate, load-bearing decision, not a default left in place by omission — do not switch to transaction-mode pooling to save connection overhead without re-deriving this reasoning first.** Configured via `backend/app/core/db.py`'s engine pooling settings (Phase 0).

**Gap surfaced during Phase 0 implementation — pre-authentication access to `users` has no organization context to scope by.** The standard `tenant_isolation` policy (above) requires `app.current_org_id` to already be set, but three real operations happen *before* any organization context exists: (a) `POST /auth/login` looking up a user by email with no org known yet (structurally true regardless of the global-vs-per-org email uniqueness decision in §1.2 — even a globally-unique email lookup has to run against the whole `users` table, not one tenant's slice of it); (b) `POST /auth/signup` inserting the very first `users` row for a brand-new organization, before any token or session exists to derive an org id from; (c) `POST /auth/invitations/{token}/accept` looking up a pending invitation by token hash, which is deliberately not scoped to an org the caller doesn't yet have credentials for.

**Resolution:** a second, narrowly-scoped permissive RLS policy on `users` only (no other table needs this — every other table is only ever queried after authentication, when an org context genuinely exists):

```sql
CREATE POLICY auth_service_bypass ON users
    USING (current_setting('app.bypass_rls_for_auth', true) = 'true')
    WITH CHECK (current_setting('app.bypass_rls_for_auth', true) = 'true');
```

Postgres RLS policies are permissive and OR'ed by default, so this adds a narrow escape hatch alongside `tenant_isolation` rather than replacing it. The application sets `SET LOCAL app.bypass_rls_for_auth = 'true'` (instead of `app.current_org_id`) only inside the three operations named above — never in any request that has an authenticated org context, and never for any table other than `users`. This is a deliberately narrow, documented exception, not a general-purpose bypass: it does not use a second database role or `BYPASSRLS`, specifically so the exception is visible in this table's policy definition rather than hidden in connection-string configuration that's easy to forget is there. Any future pre-authentication cross-tenant read (should one arise) must be justified and added here explicitly, not solved by widening this policy's condition or reusing it for a table it wasn't designed for.

### 0.2 Soft Delete Convention

All `SELECT` queries in the repository layer must filter `WHERE deleted_at IS NULL` by default; a separate `include_deleted` repository method exists for the 30-day recovery window described in Blueprint §12.3. Hard deletion is a scheduled job that purges rows where `deleted_at < now() - interval '30 days'`, except where a legal hold flag (Phase 3+) prevents it.

### 0.3 `updated_at` Trigger

Applied to every table via a shared function, not per-table application logic:

```sql
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- per table:
CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON customers
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

---

## 1. Tenancy & Identity

### 1.1 `organizations`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT NOT NULL | |
| industry | TEXT | |
| company_size | TEXT | CHECK IN ('1-10','11-50','51-250','251+') |
| timezone | TEXT NOT NULL DEFAULT 'UTC' | |
| plan | TEXT NOT NULL DEFAULT 'trial' | CHECK IN ('trial','starter','growth','enterprise') |
| business_health_score | SMALLINT | cached, recomputed by nightly Decision Engine batch job |
| onboarding_method | TEXT | CHECK IN ('integration','documents','manual_customers') — nullable until the org completes its first-run path; see §1.3 |
| onboarding_completed_at | TIMESTAMPTZ | NULL until the first-insight milestone is reached (§1.3) |
| onboarding_first_insight_at | TIMESTAMPTZ | timestamp of the first real, non-empty insight surfaced to the user — the "aha moment" metric, kept separate from `onboarding_completed_at` since a user might reach a first insight without formally finishing every onboarding step |
| terms_accepted_version | TEXT | which version of the Terms of Service (including the AI-action liability terms — see `NeuronOS_Trust_Security_FAQ.md`) this org's Owner accepted |
| terms_accepted_at | TIMESTAMPTZ | |
| dpa_signed_at | TIMESTAMPTZ | nullable — set once a Data Processing Agreement is executed for this org; most orgs won't have one until they specifically request it (see Blueprint §17.6) |
| created_at / updated_at / deleted_at | — | standard |

**Indexes:** none beyond PK (low cardinality table).
**Deletion:** hard delete only via explicit "Delete Account" flow (Settings → Danger Zone), which cascades to all child tables — this is the one place `ON DELETE CASCADE` is intentional at the top of the tree, gated behind a confirmation step and a background job, not a synchronous request.

### 1.2 `users`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE | |
| email | CITEXT NOT NULL UNIQUE | **Decision (this pass):** global uniqueness, not per-organization. See rationale below. |
| password_hash | TEXT | nullable — NULL until an invited user completes `POST /auth/invitations/{token}/accept` (API Spec §1); a user row exists from the moment they're invited, but has no usable credential until acceptance |
| name | TEXT NOT NULL | |
| role | TEXT NOT NULL DEFAULT 'member' | CHECK IN ('owner','admin','member') |
| avatar_url | TEXT | |
| last_login_at | TIMESTAMPTZ | |
| invited_by | UUID REFERENCES users(id) | |
| invitation_token_hash | TEXT | nullable — hash of the pending invitation token; cleared on acceptance. Never store the raw token. |
| invitation_expires_at | TIMESTAMPTZ | nullable — invitations expire (default 7 days); an expired, unaccepted invite requires a fresh `POST /auth/invite`, not a token refresh |
| status | TEXT NOT NULL DEFAULT 'invited' | CHECK IN ('invited','active','suspended') |
| created_at / updated_at / deleted_at | — | standard |

**Constraints:** `email` is `UNIQUE` globally (see decision note below); exactly one `owner` per organization enforced at the application layer (not a DB constraint, since ownership transfer needs a brief two-owner window during transfer).
**Indexes:** `(organization_id, role)` — used constantly for permission checks.

**Decision record — global vs. per-organization email uniqueness (resolved this pass):** the original design made `email` unique per organization specifically to leave room for one person belonging to multiple organizations (e.g., a consultant working two client accounts). But multi-org membership for a single user is explicitly *not* a supported scenario at MVP (see the former Open Item #4, now resolved by this same decision) — and per-org uniqueness broke `POST /auth/login`, which authenticates by `{email, password}` alone with no organization selector, and had no way to disambiguate if the same email existed as separate rows in two different orgs. Rather than carry that unresolved ambiguity into the auth implementation, `email` is now globally unique. One email = one account = one organization at MVP. This is a cheap constraint to relax later (drop the global `UNIQUE`, add back an org-scoped one, add an org-picker step to login) if multi-org-per-person ever becomes a real, prioritized feature — it is not being designed around speculatively now.

### 1.3 Cold-Start Onboarding State

**Gap addressed:** a brand-new organization with zero data has nothing for Pulse, the AI Workspace, or Customer risk scoring to reason about — there was no schema support for tracking a guided first-run path or measuring how quickly a new org reaches a real insight. Full flow design is in `NeuronOS_Onboarding_Spec.md`; this section covers only the data model.

- `onboarding_method` records **which** of the three supported first-run paths the org took (connect one integration / upload key documents / add top 5 customers manually) — all three are valid, equally-supported entry points, not a single forced path.
- `onboarding_first_insight_at` is the metric that matters most: the Strategic Gap Analysis flagged "time-to-insight" as a core success metric (Master Blueprint §1.9), and this column is what makes that measurable per organization rather than only in aggregate.
- No separate `onboarding_steps` table is introduced at MVP — a small, fixed checklist (3–5 items depending on `onboarding_method`) is tracked client-side against these two timestamp fields plus simple existence checks (does this org have ≥1 document? ≥1 customer? ≥1 connected integration?) rather than a new normalized table. Revisit if the onboarding flow grows more branching logic than this.

---

## 2. Customers Module

### 2.1 `customers`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE | |
| name | TEXT NOT NULL | |
| owner_user_id | UUID REFERENCES users(id) ON DELETE SET NULL | account owner internally |
| status | TEXT NOT NULL DEFAULT 'active' | CHECK IN ('active','at_risk','inactive','churned') |
| relationship_score | SMALLINT | 0–100, computed by Decision Engine |
| revenue_total | NUMERIC(14,2) DEFAULT 0 | |
| currency | CHAR(3) DEFAULT 'INR' | |
| last_contact_at | TIMESTAMPTZ | |
| source | TEXT NOT NULL DEFAULT 'manual' | CHECK IN ('manual','integration') |
| source_integration_id | UUID REFERENCES integration_connections(id) | nullable |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Indexes:** `(organization_id, status)`, `(organization_id, relationship_score)` — both support Pulse's "at risk" queries.

### 2.2 `timeline_events`

Append-only log of every interaction with a customer (meeting held, email sent, proposal shared, invoice issued, note added).

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| customer_id | UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE | |
| event_type | TEXT NOT NULL | CHECK IN ('meeting','email','proposal','invoice','note','contract') |
| title | TEXT NOT NULL | |
| body | TEXT | |
| occurred_at | TIMESTAMPTZ NOT NULL | |
| linked_entity_type | TEXT | nullable, e.g. 'meeting', 'document' |
| linked_entity_id | UUID | nullable, polymorphic — see §7.3 pattern |
| created_at / created_by | — | no updated_at — this table is append-only by design |

**Indexes:** `(organization_id, customer_id, occurred_at DESC)` — the single most common query pattern (render a customer's timeline newest-first).
**Lifecycle:** never hard-deleted independently of the parent customer; cascades on customer delete.

### 2.3 `deals`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| customer_id | UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE | |
| title | TEXT NOT NULL | |
| stage | TEXT NOT NULL DEFAULT 'proposal' | CHECK IN ('proposal','negotiation','won','lost') |
| amount | NUMERIC(14,2) NOT NULL | |
| currency | CHAR(3) DEFAULT 'INR' | |
| expected_close_date | DATE | |
| closed_at | TIMESTAMPTZ | |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Indexes:** `(organization_id, stage)`.

---

## 3. Projects Module

### 3.1 `projects`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| customer_id | UUID REFERENCES customers(id) ON DELETE SET NULL | nullable — internal projects have no customer |
| name | TEXT NOT NULL | |
| status | TEXT NOT NULL DEFAULT 'on_track' | CHECK IN ('on_track','at_risk','needs_review','in_review','completed') |
| progress_pct | SMALLINT NOT NULL DEFAULT 0 | 0–100, CHECK (progress_pct BETWEEN 0 AND 100) |
| deadline | DATE | |
| completed_at | TIMESTAMPTZ | |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Indexes:** `(organization_id, status)`, `(organization_id, deadline)`.

### 3.2 `project_members`

Join table — a project has many team members, a user is on many projects.

| Column | Type | Notes |
|---|---|---|
| project_id | UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE | |
| user_id | UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE | |
| role_on_project | TEXT DEFAULT 'contributor' | CHECK IN ('lead','contributor','reviewer') |
| added_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Primary key:** composite `(project_id, user_id)`.

### 3.3 `tasks`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| project_id | UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE | |
| title | TEXT NOT NULL | |
| assignee_id | UUID REFERENCES users(id) ON DELETE SET NULL | |
| status | TEXT NOT NULL DEFAULT 'todo' | CHECK IN ('todo','in_progress','blocked','done') |
| due_date | DATE | |
| source | TEXT NOT NULL DEFAULT 'manual' | CHECK IN ('manual','meeting_action_item','automation') |
| source_meeting_id | UUID REFERENCES meetings(id) ON DELETE SET NULL | nullable |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Indexes:** `(organization_id, project_id, status)`.

### 3.4 `risk_flags`

**Design update (same trust-calibration fix as §7.1):** a risk flag with no visible reasoning is exactly the "you're about to lose ₹8L" overconfident-claim problem flagged in the Strategic Gap Analysis §3.2. `reasoning` and `confidence_score` are added here for the same purpose as on `ai_actions`.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| project_id | UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE | |
| flag_type | TEXT NOT NULL | CHECK IN ('deadline_risk','dependency_blocked','resourcing','budget') |
| severity | TEXT NOT NULL | CHECK IN ('low','medium','high') |
| description | TEXT NOT NULL | the human-readable conclusion, e.g. "Deadline at risk" |
| reasoning | TEXT | the signal behind the conclusion, e.g. "Task 'Client data export' has been in Blocked status for 4 days; 3 of 6 remaining tasks depend on it; deadline is 2 days away." — rendered next to the flag, not hidden |
| confidence_score | REAL | 0.0–1.0, nullable for rule-based v1 (see `ai_actions.confidence_score` note on starting with a coarse rule-count-based mapping) |
| resolved_at | TIMESTAMPTZ | |
| created_at / created_by | — | generated by Decision Engine, so created_by may be a system user id |

**Indexes:** `(organization_id, project_id) WHERE resolved_at IS NULL` — partial index for the common "unresolved risks" query.

---

## 4. Meetings Module

### 4.1 `meetings`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| customer_id | UUID REFERENCES customers(id) ON DELETE SET NULL | nullable |
| title | TEXT NOT NULL | |
| platform | TEXT | e.g. 'zoom','google_meet','teams','call' |
| scheduled_at | TIMESTAMPTZ NOT NULL | |
| duration_minutes | SMALLINT | |
| status | TEXT NOT NULL DEFAULT 'upcoming' | CHECK IN ('upcoming','brief_ready','completed','needs_notes') |
| source_calendar_event_id | TEXT | external calendar ID, nullable |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Indexes:** `(organization_id, scheduled_at)`.

### 4.2 `meeting_attendees`

| Column | Type | Notes |
|---|---|---|
| meeting_id | UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE | |
| attendee_type | TEXT NOT NULL | CHECK IN ('user','customer_contact') |
| user_id | UUID REFERENCES users(id) ON DELETE CASCADE | nullable, set if attendee_type='user' |
| customer_contact_name | TEXT | nullable, set if attendee_type='customer_contact' |
| customer_contact_email | CITEXT | nullable |

**Primary key:** `id UUID PK` (not composite — a customer contact has no user_id to key off).

### 4.3 `meeting_summaries`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| meeting_id | UUID NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE | one summary per meeting |
| summary_text | TEXT NOT NULL | AI-generated |
| talking_points | JSONB | array of strings |
| generated_by_model | TEXT | which model/version generated it — important for debugging quality issues |
| generated_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| edited_by_user_id | UUID REFERENCES users(id) | nullable — set if a human edited the AI summary |

### 4.4 `meeting_action_items`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| meeting_id | UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE | |
| description | TEXT NOT NULL | |
| task_id | UUID REFERENCES tasks(id) ON DELETE SET NULL | nullable link once promoted to a Task |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

---

## 5. Documents & Knowledge Module

### 5.1 `documents`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| title | TEXT NOT NULL | |
| file_type | TEXT NOT NULL | CHECK IN ('pdf','docx','pptx','xlsx','email','other') |
| storage_key | TEXT NOT NULL | Cloudflare R2 object key, not a public URL |
| size_bytes | BIGINT | |
| ai_summary | TEXT | |
| visibility | TEXT NOT NULL DEFAULT 'org' | CHECK IN ('org','admin_only','custom') |
| source | TEXT NOT NULL DEFAULT 'manual' | CHECK IN ('manual','integration') |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Indexes:** `(organization_id, file_type)`.

### 5.2 `document_chunks`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE | |
| chunk_index | INTEGER NOT NULL | ordering within the document |
| content | TEXT NOT NULL | |
| embedding | VECTOR(1536), nullable | **Resolved during Phase 1 Knowledge implementation (migration `0003`):** was `NOT NULL`, but Roadmap Phase 1's actual Knowledge scope is keyword search, not semantic search — embeddings are a real feature (OpenAI's embeddings API, model chosen to match this dimension) gated behind an optional `OPENAI_API_KEY`. Requiring an embedding to exist before a chunk could even be stored made keyword-only search impossible without an API key, contradicting Phase 1's own scope. `NULL` here just means "not yet embedded," not "broken." |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Indexes:**
```sql
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```
Deferred until chunk volume justifies it per Blueprint §12.4 — a plain sequential scan is acceptable at MVP scale.

### 5.3 `document_tags`

| Column | Type | Notes |
|---|---|---|
| document_id | UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE | |
| tag | TEXT NOT NULL | |

**Primary key:** composite `(document_id, tag)`.

### 5.4 `linked_entities` (polymorphic linking table)

Used to connect a Document to whatever it relates to (Customer, Project, Meeting), and reused by the Context Engine for other entity-to-entity links.

**Design update (correction loop):** this table already had a `confidence` field for AI-inferred links, but no schema support existed for a user to correct a wrong one — meaning a mis-linked document (e.g., attributed to the wrong customer) would silently feed wrong context into every downstream engine (Decision, Action) with no way to fix it short of a database admin. `status`, `corrected_by_user_id`, and `corrected_at` close that gap.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| source_type | TEXT NOT NULL | e.g. 'document' |
| source_id | UUID NOT NULL | |
| target_type | TEXT NOT NULL | e.g. 'customer','project','meeting' |
| target_id | UUID NOT NULL | |
| relationship | TEXT | e.g. 'related_to','contract_for','proposal_for' |
| confidence | REAL | 0.0–1.0, set when the link was AI-inferred rather than user-confirmed |
| status | TEXT NOT NULL DEFAULT 'ai_suggested' | CHECK IN ('ai_suggested','confirmed','rejected','manual') — `manual` covers links a user created directly rather than the Context Engine inferring one; `confirmed`/`rejected` are the outcomes of a user reviewing an `ai_suggested` link |
| corrected_by_user_id | UUID REFERENCES users(id) | nullable; set when a user confirms or rejects an AI-suggested link |
| corrected_at | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Note:** This table intentionally has no foreign key constraints on `source_id`/`target_id` since the type varies — referential integrity here is enforced at the application layer, with a periodic consistency-check job as a safety net. This is a deliberate, documented exception to the "FKs everywhere" rule, justified by the genuine need for a polymorphic link across entity types the Context Engine discovers dynamically.
**Indexes:** `(organization_id, source_type, source_id)` and `(organization_id, target_type, target_id)` — both directions of lookup are common. Add `(organization_id, status) WHERE status = 'ai_suggested' AND confidence < 0.7` (partial index) to efficiently surface low-confidence links that most need a human look — this is the query the correction-review UI runs.
**Behavioral rule:** a low-confidence `ai_suggested` link (below a configurable threshold, e.g. 0.6) should not be treated with the same weight as a `confirmed` or `manual` link by the Context/Decision Engines when computing downstream scores — this avoids a single shaky inference silently having full influence on a customer's risk score before a human has ever looked at it.

---

## 6. Automations Module

### 6.1 `automations`

**Design update (resolves the approve-first contradiction flagged in the Strategic Gap Analysis §1):** an automation cannot jump straight to fully unsupervised execution the moment a user flips it on. Every automation starts in `dry_run` mode, then moves to a `graduating` mode where its first N real triggers still route through the `ai_actions` approval queue (reusing the existing AI Actions infrastructure — no new approval mechanism needed), and only becomes `live` (fires without per-instance review) once it has enough approved history. This is enforced by the schema, not left to application-layer discipline alone.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| name | TEXT NOT NULL | |
| mode | TEXT NOT NULL DEFAULT 'dry_run' | CHECK IN ('dry_run','graduating','live','paused') — see state machine below |
| is_active | BOOLEAN NOT NULL DEFAULT true | whether the automation is enabled at all, independent of `mode` |
| trigger_type | TEXT NOT NULL | CHECK IN ('invoice_overdue','no_reply_days','project_completed','contract_expiring','new_customer') |
| trigger_config | JSONB NOT NULL | e.g. `{"days": 3}` |
| action_type | TEXT NOT NULL REFERENCES action_type_registry(action_type) | **Resolved during Phase 1 Automations implementation:** this was previously its own, separate `CHECK` constraint (`send_email`, `create_task`, `notify_user`, `send_invoice_reminder`) that never actually matched `action_type_registry`'s real values (`send_followup_email`, `create_task`, `prepare_meeting_brief`, `send_contract_email`, `generate_invoice`, `send_invoice_reminder`) — the exact drift this table's Open Item #18 warned about, now surfaced for real once a `graduating`-mode automation needed to create an `ai_actions` row using this value. Fixed the same way `ai_actions.action_type` already was (§7.1): a real foreign key into `action_type_registry`, so there is exactly one place these values are defined, not two lists that can silently disagree. |
| action_config | JSONB NOT NULL | |
| graduation_threshold | INTEGER NOT NULL DEFAULT 5 | number of approved runs required in `graduating` mode before auto-promoting to `live` |
| approved_run_count | INTEGER NOT NULL DEFAULT 0 | increments each time a `graduating`-mode run is approved via the AI Actions queue; resets to 0 if a run is rejected (a rejection is a signal the trigger/action logic needs revisiting, not just "one more try") |
| times_triggered | INTEGER NOT NULL DEFAULT 0 | |
| success_rate_pct | SMALLINT | cached, recomputed periodically |
| created_at / updated_at / deleted_at / created_by | — | standard |

**Mode state machine:**
```
dry_run  →  graduating  →  live
   ↑              ↓ (on any rejection)
   └──────────────┘
              ↓ (user can pause from any state)
            paused
```
- **`dry_run`:** every trigger match is logged to `automation_runs` (see §6.2) with `status = 'simulated'`, showing exactly what *would* have happened (who would have received what email, etc.) — nothing is sent. This directly implements the "show what it would have done this week without sending anything" recommendation from the Strategic Gap Analysis.
- **`graduating`:** every trigger match creates a real `ai_actions` row (status `suggested`) instead of executing directly — a human approves or rejects it exactly like any other AI Action. An approval increments `approved_run_count`; a rejection resets it to 0 and keeps the automation in `graduating` mode indefinitely until it earns a clean streak.
- **`live`:** triggers execute directly via `automation_runs`, no per-instance approval required — this is the only mode where the original "Active, 96% success" UI pattern is accurate to what's actually happening.
- A user (Admin/Owner) can force any automation back to `dry_run` at any time — graduation is not a one-way, permanent trust grant.

**Note:** Trigger/condition/action are modeled as JSONB config on one row rather than three separate tables for MVP — this matches the "canned templates" scope (Blueprint Phase 1) and is deliberately simple. The Phase 2 custom automation builder will likely require normalizing `trigger_config`/`action_config` into structured tables once conditions can be chained (AND/OR logic) — flagged as a schema migration to plan for, not built prematurely now.

### 6.2 `automation_runs`

Log of every time an automation fired — needed for the "Triggered 48 times, Success 96%" stats shown in the Automations UI, and now also the record of every `dry_run` simulation.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| automation_id | UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE | |
| idempotency_key | TEXT NOT NULL | see §7.4 — deterministically derived from `(automation_id, trigger_entity_id, trigger_window)` so a retried background job cannot fire the same automation twice for the same trigger event |
| triggered_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| status | TEXT NOT NULL | CHECK IN ('simulated','success','failed','pending_approval') — `simulated` is used in `dry_run` mode, `pending_approval` bridges to the `ai_actions` row created while `graduating` |
| related_ai_action_id | UUID REFERENCES ai_actions(id) ON DELETE SET NULL | set when `status = 'pending_approval'` (graduating mode) |
| error_message | TEXT | nullable |
| target_entity_type | TEXT | e.g. 'customer' |
| target_entity_id | UUID | |

**Constraint:** `UNIQUE (automation_id, idempotency_key)` — the database itself refuses a duplicate execution for the same trigger event, not just application-layer discipline.

---

## 7. AI Actions Queue

### 7.1 `ai_actions`

The central queue every engine writes to and every "Approve" button reads from.

**Design update (trust calibration + severity gating):** two gaps from the Strategic Gap Analysis are addressed directly in this table. First (§3.2, "cried wolf" risk): a risk score or recommendation with no visible reasoning reads as an unexplained, overconfident claim — the first wrong one erodes trust in every subsequent one. Second (§3.4, irreversibility): sending a reminder email and generating an invoice are very different risk levels but were being treated identically by the approve/reject flow.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| title | TEXT NOT NULL | |
| description | TEXT | |
| action_type | TEXT NOT NULL REFERENCES action_type_registry(action_type) | **Fixed this pass:** previously a freeform TEXT column with no constraint at all (just "e.g." examples in this column's notes), meaning the severity mapping table below was documentation-only with nothing in the schema enforcing it. Now a real foreign key into `action_type_registry` (§7.1 below) — the registry is the single source of truth for which `action_type` values exist and what severity/reversibility each carries, rather than maintaining the same list in two places (a CHECK constraint here and a separate mapping table would drift out of sync). |
| severity_tier | TEXT NOT NULL DEFAULT 'low' | CHECK IN ('low','medium','high') — see severity mapping below; drives UI confirmation friction, not just a display label |
| is_reversible | BOOLEAN NOT NULL DEFAULT true | e.g. an internal task creation is reversible (delete it); a sent email or generated invoice is not — this is set per `action_type`, not per instance, and should be treated as close to a constant lookup table keyed on `action_type` |
| reasoning | TEXT | the signal the engine actually saw — e.g. "No timeline event logged for 12 days; last 3 emails from this customer went unanswered; deal stage has not advanced in 18 days." Rendered in the UI alongside the conclusion, not hidden behind a "why?" click — see Master Blueprint §2.7 |
| confidence_score | REAL | 0.0–1.0; nullable in cases where the generating engine doesn't yet produce a calibrated confidence (rule-based v1 scoring can start with a coarse mapping — e.g., how many rules fired — rather than skipping this field entirely) |
| priority | TEXT NOT NULL DEFAULT 'medium' | CHECK IN ('low','medium','high') |
| status | TEXT NOT NULL DEFAULT 'suggested' | CHECK IN ('suggested','approved','rejected','delegated','executed','failed') |
| suggested_amount | NUMERIC(14,2) | nullable, used for revenue-related actions (e.g. invoice) |
| related_entity_type | TEXT | e.g. 'customer','project','meeting' |
| related_entity_id | UUID | polymorphic, same pattern as §5.4 |
| assigned_to_user_id | UUID REFERENCES users(id) | who it's suggested for |
| delegated_to_user_id | UUID REFERENCES users(id) | nullable |
| decided_by_user_id | UUID REFERENCES users(id) | who approved/rejected |
| decided_at | TIMESTAMPTZ | |
| executed_at | TIMESTAMPTZ | |
| generated_by_engine | TEXT NOT NULL | which engine produced this suggestion — feeds Learning Engine analysis |
| created_at / updated_at | — | standard, no soft delete — history is kept permanently for the Learning Engine |

**Indexes:** `(organization_id, status)`, `(organization_id, assigned_to_user_id, status)`.

**Severity mapping (starting point, refine with real usage):**

| `action_type` | `severity_tier` | `is_reversible` | UI friction implied (see Blueprint §2.7 / §5.9) |
|---|---|---|---|
| `send_followup_email` (routine check-in) | low | false | Standard single-click Approve |
| `create_task` | low | true | Standard single-click Approve |
| `prepare_meeting_brief` | low | true | Standard single-click Approve |
| `send_contract_email` | high | false | Requires opening the drafted content and an explicit secondary confirmation, not a single click |
| `generate_invoice` | high | false | Same as above — financially significant and irreversible once sent |
| `send_invoice_reminder` | medium | false | One click, but visually distinguished (e.g., amber accent) from low-severity actions |

**Schema enforcement (added this pass — the table above was previously convention-only):** the mapping is now backed by a small reference table rather than left to each engine to set correctly per instance:

```sql
CREATE TABLE action_type_registry (
    action_type    TEXT PRIMARY KEY,
    severity_tier  TEXT NOT NULL CHECK (severity_tier IN ('low','medium','high')),
    is_reversible  BOOLEAN NOT NULL
);
```

`ai_actions.action_type` is a foreign key into this table (see the column definition above) — this is the single source of truth for which action types exist and what severity/reversibility each carries. When any engine creates a new `ai_actions` row, the application layer looks up `severity_tier`/`is_reversible` from `action_type_registry` and copies them onto the new row — **the engine does not set these two fields directly, and cannot insert an `ai_actions` row with an `action_type` that isn't already registered.** This closes the gap where a rushed addition of a new action type could silently default to `low`/reversible and skip the higher-friction confirmation a genuinely high-stakes action needs. Adding a new `action_type` requires a migration that inserts a row into `action_type_registry` first — there is no path to using an unregistered action type at all, by construction.

### 7.2 `ai_action_executions`

Execution audit log — required by Blueprint §17.4.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| ai_action_id | UUID NOT NULL REFERENCES ai_actions(id) ON DELETE CASCADE | |
| idempotency_key | TEXT NOT NULL UNIQUE | see §7.4 — generated once when the action is approved (`POST /ai-actions/{id}/approve`) and reused on any retry of the execution job, so a retried Celery task or a double-clicked Approve button cannot execute the same action twice |
| executed_action | TEXT NOT NULL | what actually happened, e.g. "Sent email to jane@abcltd.com" |
| payload | JSONB | full request/response of the underlying integration call, for debugging |
| result | TEXT NOT NULL | CHECK IN ('success','failed') |
| error_message | TEXT | |
| executed_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

### 7.3 Polymorphic Reference Pattern (used in §2.2, §5.4, §7.1)

NeuronOS uses a consistent `(_type, _id)` pair rather than a single generic foreign key for any place an entity needs to reference "one of several possible tables." This is a deliberate trade-off: it sacrifices database-enforced referential integrity for the flexibility the Context Engine needs (linking arbitrary entity types it discovers at runtime). Mitigations: (a) a nightly consistency-check job that flags orphaned polymorphic references, (b) application-layer validation on every write, (c) this pattern is used only for entities that need it — the majority of the schema uses standard FKs.

### 7.4 Idempotency Pattern (applies to every job with an external side effect)

**Gap addressed:** background jobs (integration syncs, AI Action execution, automation runs) had no documented guarantee against double-execution. A retried Celery task or a double-clicked "Approve" button could otherwise send the same email twice — and unlike most operations in the system, sending an email or creating an external record cannot be undone.

**Standard applied across the schema:**

- Every table that logs the *result* of an external side effect (`ai_action_executions`, `automation_runs`) carries an `idempotency_key` column with a uniqueness constraint.
- The key is generated **once**, at the moment the action is approved or the automation trigger first fires — not regenerated on each retry. A retried job passes the same key; the database's `UNIQUE` constraint causes the retry's insert to fail harmlessly (caught and treated as "already executed, skip"), rather than executing twice.
- Recommended key construction: a deterministic hash of `(entity_type, entity_id, action_type, trigger_window)` rather than a random UUID generated per attempt — a random key would defeat the whole purpose, since a retry needs to produce the *same* key as the original attempt to be recognized as a duplicate.
- This pattern should extend to any future job type that calls an external API with a side effect (e.g., a Phase 2 integration sync that creates records in a third-party CRM) — it is a general rule for the codebase, not specific to these two tables.

### 7.5 Score & Algorithm Versioning

**Gap addressed:** if the Relationship Score or Business Health Score formula changes (a near-certainty, per the Roadmap's move from rule-based to ML-based scoring in Phase 3), historical trend charts would otherwise show an apparent change in business health that's actually just a change in measurement — with no way for a user or the team to tell the difference.

- `organizations.business_health_score` and `customers.relationship_score` are joined by a new column: `score_algorithm_version TEXT NOT NULL DEFAULT 'v1_rule_based'` — updated whenever the underlying scoring logic changes materially (not on every minor weight tweak, but whenever the Decision Engine's approach changes in a way that would make an old score and a new score not directly comparable).
- Historical score values are retained in a new lightweight append-only table, `score_history`, rather than only keeping the latest cached value on the parent row:

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| entity_type | TEXT NOT NULL | CHECK IN ('organization','customer') |
| entity_id | UUID NOT NULL | |
| score | SMALLINT NOT NULL | |
| algorithm_version | TEXT NOT NULL | |
| computed_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

- Any trend chart (Reports, Pulse sparkline) rendering `score_history` should visually flag the point where `algorithm_version` changes (e.g., a small marker/annotation) so a business owner reading "business health dropped" can tell whether that's a real change or a measurement-method change.
- **Retention (flagged during verification — not fully designed here):** `score_history` is append-only and will grow without bound if a snapshot is written on every recompute (e.g., nightly per customer). Recommend either (a) capping write frequency (e.g., one snapshot per entity per day even if recomputed more often), or (b) a downsampling job that collapses old daily snapshots into weekly/monthly ones after a retention window (e.g., 90 days of daily detail, then monthly thereafter) — exact policy is a Phase 2 decision once real data volume is known, but the table should not be built assuming infinite unthrottled writes.

### 7.6 Reliability & Staleness Fields (supports SLOs — see Master Blueprint §9.1)

**Gap addressed:** there was no defined way to represent "how stale is this data" or "is this module currently meeting its reliability target" anywhere in the schema.

- `integration_connections` already had `last_synced_at` and `last_sync_error` (§8.1) — these are the source of truth for the "stale data warning" the Roadmap doc flagged as an open question. **Resolution of that open question:** the frontend should treat any integration whose `last_synced_at` is older than a per-provider configurable staleness threshold (default: 2 hours for calendar/email, 24 hours for CRM/accounting) as stale, and Pulse should visibly caveat any insight that depends on stale-sourced data (e.g., "based on data synced 6 hours ago") rather than presenting it with the same confidence as fresh data.
- No new table is needed for this — it's a read-time computation (`now() - last_synced_at > threshold`) against existing columns, kept here rather than materialized, since staleness is inherently a function of "now."

---

## 8. Integrations

### 8.1 `integration_connections`

**Gap addressed:** the original provider list omitted Microsoft/Outlook entirely, and nothing in the schema tracked where a provider stood in its own app-review process — a real, calendar-time-driven blocker (see Master Blueprint §9.1 and Roadmap §2A for the full explanation of why this matters).

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | |
| provider | TEXT NOT NULL | CHECK IN ('gmail','google_drive','google_calendar','outlook','microsoft_365','slack','whatsapp','hubspot','salesforce','zoho_crm','zoho_books','quickbooks') |
| connected_by_user_id | UUID REFERENCES users(id) | |
| scopes | TEXT[] | granted OAuth scopes — see note below on minimizing scope tier |
| access_token_encrypted | TEXT NOT NULL | encrypted at the application layer before storage, never plaintext |
| refresh_token_encrypted | TEXT | |
| status | TEXT NOT NULL DEFAULT 'connected' | CHECK IN ('connected','sync_error','disconnected') |
| last_synced_at | TIMESTAMPTZ | see §7.6 for how this drives staleness warnings |
| last_sync_error | TEXT | surfaced to the user per the "stale data warning" resolution in §7.6 |
| provider_review_status | TEXT NOT NULL DEFAULT 'not_submitted' | CHECK IN ('not_submitted','in_review','approved','rejected') — tracks NeuronOS's own app-level standing with the provider (e.g., Google verification status), not the end user's connection. This is an org-independent, deployment-wide fact, but is stored per-row for simplicity in MVP since one org's connection attempt is the natural place the team notices review status; a dedicated `provider_app_registrations` table is the correct home for this once more than one deployment environment (staging/prod) needs to track it independently. |
| created_at / updated_at / deleted_at | — | standard; `deleted_at` set on disconnect, not a hard delete, to retain audit trail of what was once connected |

**Constraints:** `UNIQUE (organization_id, provider) WHERE deleted_at IS NULL` — one active connection per provider per org at MVP (multiple accounts per provider is a Phase 3+ consideration).
**Security note:** token encryption keys are managed outside the database (KMS/secrets manager), never stored alongside the encrypted value.
**Scope minimization note:** for `gmail`, prefer `gmail.readonly` or a metadata-only scope over full `https://mail.google.com/` access if the product surface can be built on the narrower scope — this is a genuine product/design decision, not just a compliance checkbox, because it can drop the integration into a materially lighter provider review tier (see Master Blueprint §9.1).

---

## 8A. AI Workspace (Chat)

**Gap addressed:** API Spec §6 documents `POST /chat/messages`, `GET /chat/conversations`, and `GET /chat/conversations/{id}`, but this document never defined a table for either entity — the AI Workspace had zero backing schema (Phase 1 Roadmap scope, resolved via migration 0005).

### 8A.1 `conversations`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| organization_id | UUID NOT NULL | tenant-scoped, standard `tenant_isolation` RLS policy |
| user_id | UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE | owner of the conversation |
| title | TEXT | derived from the first message; nullable |
| created_at / updated_at | — | standard; `updated_at` bumps whenever a new message is appended, so `GET /chat/conversations` can order by "most recently active" |

**Permissions note:** "own conversations only" (API Spec §6) is enforced at the application layer by filtering on `user_id` — RLS's `tenant_isolation` policy only enforces the organization boundary, the same division of responsibility used for `ai_actions.assigned_to_user_id` scoping.

### 8A.2 `chat_messages`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| conversation_id | UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE | |
| role | TEXT NOT NULL | CHECK IN ('user','assistant') |
| content | TEXT NOT NULL | |
| citations | JSONB | list of `{type, id, excerpt}`; null for user messages |
| created_at | TIMESTAMPTZ NOT NULL | |

Only indirectly tenant-scoped (joined through `conversation_id`) — no RLS policy of its own, consistent with `document_chunks` relative to `documents` (§5.2).

---

## 9. Migration & Versioning Notes

**Decision record — full schema built in Phase 0, app code scoped per phase (resolved this pass):** this document covers all MVP + Phase 2 entities in one pass, but the Roadmap explicitly excludes the Projects, Meetings, and Automations-builder modules from Phase 1. Rather than leave it ambiguous whether Phase 0's initial migration should create only Phase-1-relevant tables or everything, the decision is: **Phase 0 creates the full schema below — every table in this document — via Alembic, in one coherent migration set.** Application/API/service-layer code is still built strictly per the Roadmap's phase scope (e.g., no `Project`/`Meeting`/`Automation` routes or services exist until their phase arrives) — the tables simply sit unused until then. This is the cheaper direction to be wrong in: adding a nullable column or a new table later is a low-risk additive migration, while retrofitting foreign keys (e.g., `projects.customer_id`, `tasks.source_meeting_id`) onto tables that already have production data is genuinely painful. The risk this accepts is a schema that's briefly ahead of the product surface — acceptable, since unused tables carry no runtime cost and this repo's migration history is the actual source of truth for "what exists," not a proxy for "what's shipped" (that's what the Roadmap phase gates are for).

- All schema changes go through Alembic; every migration must be reversible (`downgrade()` implemented, not `pass`).
- Additive changes (new nullable column, new table) can ship without a maintenance window; changing a `CHECK` constraint's allowed values or altering a column type requires a backfill migration plan documented in the PR.
- `document_chunks.embedding` dimensionality is locked in at the first migration that creates the table — changing embedding models later requires a full re-embedding backfill job, not a simple column alter. Flag this decision for sign-off before Phase 1 ships (this is the single hardest-to-reverse schema decision in the system).

---

## 10. Open Items Carried Into Implementation

1. Confirm embedding model (and therefore `VECTOR(n)` dimension) before the first migration touching `document_chunks` — this is expensive to change later.
2. Decide whether `automations` trigger/condition/action should be normalized into separate tables now vs. at the start of Phase 2 (see §6.1 note) — recommend deferring, but the team should explicitly agree, not default into it.
3. Legal hold / litigation-hold flag on soft-deleted rows is noted as a Phase 3+ need (§0.2) — not designed in detail here.
4. **[Resolved this pass]** Multi-org membership for a single user (a consultant working across two client orgs) is not supported by the current `users` table design — confirmed acceptable for MVP, and `email` is now globally `UNIQUE` (not per-org) as a direct consequence, since per-org uniqueness only existed to leave room for a feature that isn't being built. See §1.2's decision record. Revisit if multi-org-per-person becomes a real prioritized request.
5. **[Resolved this pass]** Idempotency on execution jobs — see §7.4. Applied to `ai_action_executions` and `automation_runs`; extend the same pattern to any future job with an external side effect.
6. **[Resolved this pass]** Automation autonomy vs. approve-first contradiction — see §6.1's `mode` state machine (`dry_run` → `graduating` → `live`).
7. **[Resolved this pass]** Score/algorithm versioning — see §7.5 (`score_algorithm_version`, `score_history` table).
8. **[Resolved this pass]** Integration staleness representation — see §7.6; drives the Pulse staleness-caveat behavior.
9. **[Resolved this pass]** Missing Outlook/Microsoft 365 from the provider list, plus no way to track NeuronOS's own app-review standing per provider — see §8.1 (`outlook`, `microsoft_365` added; `provider_review_status` column added). Note the flagged follow-up: promote `provider_review_status` to its own `provider_app_registrations` table once more than one deployment environment needs independent tracking.
10. `dry_run`-mode simulated sends (§6.1/§6.2) need a clear rendering strategy in the Automations UI ("here's what would have happened") — this is a frontend/UX design task that falls out of the schema change, not a database concern, but is flagged here so it isn't lost.
11. **[Resolved this pass]** Cold-start onboarding had no schema support — see §1.3 (`onboarding_method`, `onboarding_first_insight_at` on `organizations`). Full flow design lives in `NeuronOS_Onboarding_Spec.md`.
12. **[Resolved this pass]** Trust-calibration gap — AI Actions and risk flags gave a conclusion with no visible reasoning or confidence, risking a "cried wolf" trust collapse on the first wrong call. See `ai_actions.reasoning`/`confidence_score` (§7.1) and `risk_flags.reasoning`/`confidence_score` (§3.4).
13. **[Resolved this pass]** No correction loop for AI-inferred `linked_entities` — a wrong document-to-customer link had no way to be fixed and would silently propagate into downstream scoring. See §5.4's `status`/`corrected_by_user_id`/`corrected_at` fields and the low-confidence-link weighting rule.
14. **[Resolved this pass]** Irreversibility wasn't gated by severity — sending a reminder and generating an invoice got identical approval friction. See `ai_actions.severity_tier`/`is_reversible` (§7.1) and the severity mapping table.
15. **[Resolved this pass]** No schema support for ToS acceptance or DPA tracking — see `organizations.terms_accepted_version`/`terms_accepted_at`/`dpa_signed_at` (§1.1). Full security/liability posture content is in `NeuronOS_Trust_Security_FAQ.md`.
16. **[Fixed during verification pass]** A real section-ordering bug — §1.3 (Cold-Start Onboarding State) had been inserted before §1.2 (`users`) during editing, so the document read out of sequence. Corrected.
17. **[Fixed during verification pass]** `ai_actions.action_type` had no constraint at all (freeform text with only "e.g." examples), while a separate severity-mapping table implied a fixed set of values with specific severity/reversibility — nothing in the schema actually enforced the connection between the two. Fixed by adding `action_type_registry` (§7.1) as the single source of truth, with `ai_actions.action_type` as a real foreign key into it, and application logic populating `severity_tier`/`is_reversible` from the registry rather than trusting each engine to set them correctly per instance.
18. **[Resolved during Phase 1 Automations implementation]** `automations.action_type`'s value set (`send_email`, etc.) never actually matched `ai_actions.action_type`'s registry values, exactly as this item warned. Rather than define a mapping between two permanently-separate vocabularies, `automations.action_type` is now a real foreign key into `action_type_registry` (migration `0002_automations_action_type_fk`) — the same registry `ai_actions.action_type` already uses, so a `graduating`-mode automation's `action_type` is, by construction, always a value `ai_actions` already understands.
19. **New open item (surfaced during verification):** `score_history` (§7.5) is append-only with no retention/downsampling policy — will grow unbounded if a snapshot is written on every recompute. Needs a policy (cap write frequency, or downsample old data) before Phase 2 usage volume makes this a real storage/performance concern.
20. **[Resolved this pass]** Login had no way to disambiguate a per-org-unique email across two organizations, since `POST /auth/login` takes only `{email, password}` with no org selector — resolved by making `email` globally unique (§1.2 decision record), consistent with multi-org-per-person being out of scope for MVP (item 4 above).
21. **[Resolved this pass]** No endpoint or schema support existed for an invited user to actually accept an invitation and set a password — `users.password_hash` starts NULL at invite time, and `invitation_token_hash`/`invitation_expires_at` (§1.2) back the new `POST /auth/invitations/{token}/accept` endpoint (API Spec §1). Without this, Phase 0's own exit criteria ("invite a teammate") could not actually be completed end-to-end.
22. **[Resolved this pass]** RLS's `SET LOCAL app.current_org_id` pattern (§0.1) had an unstated dependency on connection pooling mode — transaction-mode pooling could theoretically hand a connection with a stale org context to a different tenant's request under concurrent load. Resolved by adopting session-mode pooling as a deliberate, documented infrastructure decision (§0.1) rather than leaving it to whatever a hosting provider defaults to.
23. **[Resolved this pass]** Whether the full schema (including Phase 2-only tables like `projects`/`meetings`/`automations`) should be created in Phase 0 or phased alongside app code was undecided — resolved: full schema now via Alembic, app/API code still scoped strictly per Roadmap phase (§9's decision record).
24. **[Resolved during Phase 0 implementation]** The standard RLS policy has no way to serve `POST /auth/login`, `POST /auth/signup`, or `POST /auth/invitations/{token}/accept`, since none of them have an organization context yet — this surfaced only once the auth endpoints were actually being implemented against the schema, not during spec review. Resolved by the narrow `auth_service_bypass` policy on `users` only (§0.1 addendum) rather than a database-role-level RLS bypass, keeping the exception visible in the table's own policy definition.
25. **[Resolved during Phase 0 implementation — found by a real cross-tenant test, not by review]** RLS was silently not enforced at all: the app was connecting as the table-owning migration role, which Postgres exempts from RLS regardless of `ENABLE ROW LEVEL SECURITY`. See §0.1's `FORCE ROW LEVEL SECURITY` addition and §0.1.1's new `neuronos_app` restricted role — the application must always connect as this role, never as the owner.
26. **[Resolved during Phase 0 implementation]** `current_setting('app.current_org_id')` in the `tenant_isolation` policy was missing its `missing_ok` argument, causing every query against a table with more than one applicable policy (i.e. `users`, which also has `auth_service_bypass`) to error out in any session that had set the other policy's variable but not this one. Fixed to `current_setting('app.current_org_id', true)` — see §0.1.
