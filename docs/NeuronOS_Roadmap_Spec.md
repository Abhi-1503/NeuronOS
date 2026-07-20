# NeuronOS — Development Roadmap & Technical Spec
**Version:** 1.0 (derived from Master Blueprint v1.0)
**Status:** Pre-MVP → Build-ready
**Audience:** Engineering team (frontend, backend, AI/ML, DevOps)
**Owner:** Abhishek Singh

---

## 1. Purpose of This Document

The Master Blueprint defines *what* NeuronOS is and *why* it exists. This document translates that vision into a build plan: phased milestones, module specs, data model, API surface, AI architecture, and infrastructure decisions a dev team can execute against.

---

## 2. Product Summary (for context)

NeuronOS is an AI-native intelligence layer that sits above a company's existing tools (Gmail, Drive, CRM, Slack, accounting, calendars) — not replacing them. It ingests connected data, builds business context, and surfaces prioritized, actionable recommendations ("You're about to lose ₹8L because 3 customers haven't been contacted in 12 days") rather than passive dashboards.

Core modules: **Pulse, Memory (Knowledge), Customers, Projects, Meetings, Documents, AI Workspace, Automations, AI Actions, Reports, Settings**, with a shared six-engine AI core: **Memory, Knowledge, Context, Decision, Action, Learning**.

---

## 3. Build Philosophy

- **One AI core, many surfaces.** Every module reads/writes through the same engines — no module should have bespoke AI logic that the others can't reuse.
- **Context before automation.** Don't ship an automation that acts on a customer/project/document until the Context Engine can reliably link those entities together.
- **Approve-first, not autopilot.** AI Actions default to "Review → Approve" in early phases; full autonomy is a post-MVP trust milestone, not a v1 assumption.
- **Integrations are additive.** MVP should be usable and valuable with zero integrations connected (manual data entry), so integration outages never break the core product.

---

## 4. Phased Roadmap

### Phase 0 — Foundations (Weeks 1–4)
Infrastructure, auth, data model, design system — nothing user-facing yet.

- Repo scaffolding: Next.js 15 (frontend), FastAPI (backend), monorepo or polyrepo decision
- PostgreSQL + pgvector schema v1 (see §7)
- Auth: org/user model, roles (Owner, Admin, Member), session handling
- Design system in shadcn/ui + Tailwind tokens (colors, type scale, spacing) matching approved mockups
- CI/CD: GitHub Actions → Railway (MVP environment)
- Observability baseline: Sentry + basic logging; initial SLO targets defined (see Master Blueprint §9.2) even before there's traffic to measure against
- **Start integration provider review processes now, in parallel with everything else — do not wait for Phase 2 (see §2A below).** At minimum: register the app with Google (Gmail/Drive/Calendar) and Microsoft (Outlook/365), stand up the OAuth consent screens, and submit for verification with a working demo, even if the underlying integration features aren't built yet.

**Exit criteria:** a logged-in user can create an org, invite a teammate, and see an empty Pulse shell — **and** the Google and Microsoft app-verification submissions are in flight.

### Phase 2A — Integration Provider Review (parallel track, starts Phase 0, runs through Phase 2)

**Gap addressed:** the original plan treated integration work as pure engineering effort sized entirely by Phase 2's 10-week window. In reality, several providers run their own external review process on their own timeline — full detail and the reasoning behind each is in Master Blueprint §9.1. This is called out as its own track (not folded into Phase 2's engineering weeks) specifically so it isn't accidentally sequenced *after* the code is written, which is the mistake that would silently blow up the Phase 2 timeline.

| Provider | Review mechanism | When to start | Notes |
|---|---|---|---|
| Gmail / Google Workspace | OAuth verification + CASA assessment (restricted scopes) | Phase 0 | Longest lead time in the list if full mailbox scope is requested — revisit whether a narrower scope suffices before submitting |
| Google Drive / Calendar | Google verification pipeline, scope-dependent | Phase 0 | Can often be bundled with the Gmail submission under the same Google Cloud project |
| Outlook / Microsoft 365 | Microsoft app registration + admin consent + publisher verification | Phase 0 | Separate process from Google's — cannot be batched together |
| Salesforce | AppExchange Security Review / connected-app review | Phase 1 | Known for slow, multi-cycle review — budget generously |
| HubSpot | App certification / marketplace review | Phase 1 | |
| QuickBooks (Intuit) | Sandbox → production key review | Phase 1 | Extra scrutiny given financial data |
| Zoho CRM / Books | Developer/partner OAuth review | Phase 1–2 | Generally lighter-weight |
| Slack | App review | Phase 1–2 | Lighter-weight |
| WhatsApp Business | Meta Business verification + message template approval | Phase 2 (start early within Phase 2) | Materially higher friction than a typical OAuth integration — treat as its own workstream, not a checkbox alongside Slack |

**Owner:** this track needs an explicit owner (not "whoever's free") since it involves external correspondence, potential resubmissions, and annual re-verification once approved — recommend the same person owns it end-to-end rather than handing it off mid-process.

### Phase 1 — MVP Core (Weeks 5–12)
Ship the smallest version of the product that proves the core loop: *data in → context built → recommendation out.*

| Module | MVP Scope |
|---|---|
| **Onboarding** | Cold-start first-run flow — three supported entry paths (connect one integration / upload key documents / add top 5 customers manually), see Master Blueprint §4.4 and `NeuronOS_Onboarding_Spec.md`. **This is now an explicit MVP deliverable, not an assumed side effect of the other modules existing** — the Strategic Gap Analysis flagged this as the single biggest activation risk, and it was previously undesigned. |
| **Pulse** | Business Health score (rule-based v1), Today's Focus cards, manual "Ask NeuronOS" chat box; renders the Onboarding path selector as its actual first-run content for an org with `onboarding_completed_at IS NULL`, rather than a blank/meaningless score |
| **Customers** | CRUD, manual timeline entries, Relationship Score (rule-based v1), risk flagging |
| **Knowledge (Memory)** | Document upload (PDF/DOCX), storage, keyword search; AI summary per doc; **AI-inferred document-to-customer/project links surface with a visible confidence indicator and a review queue for confirming/rejecting low-confidence links** (resolves the Context Engine correction-loop gap — Database Spec §5.4, API Spec §5A) |
| **AI Workspace** | Chat interface over uploaded knowledge + customer data (RAG v1) |
| **AI Actions** | Suggested actions list with Approve/Review/Delegate; no auto-execution yet; **every suggestion displays its `reasoning` and `confidence_score` inline, not behind a click** (resolves the "cried wolf" trust-calibration gap — Master Blueprint §2.7); **actions marked `severity_tier = 'high'` (e.g., generating an invoice, sending a contract email) require an explicit secondary confirmation, visually distinct from routine low-severity approvals** (resolves the irreversibility-not-gated-by-severity gap — Database Spec §7.1) |
| **Automations** | 3–4 canned templates (follow-up reminder, invoice overdue, welcome new client) — **every automation ships in `dry_run` mode by default (Database Spec §6.1); a user can advance one to `graduating` mode, where its first several triggers route through the AI Actions approval queue instead of executing directly, and only after that history builds up does it reach `live` (fully unsupervised) mode.** No automation ships able to jump straight to unsupervised execution — this directly resolves the approve-first contradiction identified in the Strategic Gap Analysis. |
| **Reports** | Static overview: revenue, deals, at-risk count (manual/CSV-fed if no integrations) |
| **Settings** | Company profile, team management, integration stubs (UI only, "Coming soon" for most); integration cards show `provider_review_status` where relevant, so the team (and eventually curious users) can see review progress rather than a mysterious "coming soon" |

**Explicitly out of scope for MVP:** Projects module, Meetings module, live third-party integrations (Gmail/Slack/CRM sync — pending provider review per §2A above), Learning Engine, mobile app, voice command.

**Security/trust readiness moved up from "eventually" to a Phase 1 requirement (not deferred to Phase 4):** before any design partner connects a real Gmail account or real customer data, the team must be able to state the baseline security posture plainly (encryption at rest, least-privilege revocable OAuth scopes, a clear data retention/deletion policy) and have the liability position for AI-executed actions reflected in the Terms of Service the org's Owner accepts on signup. See Master Blueprint §17.7/§17.8 and the companion `NeuronOS_Trust_Security_FAQ.md`. This does **not** mean SOC 2 or a DPA program needs to exist by Phase 1 — only that an honest, ready answer exists when a design partner asks, rather than the question catching the team flat-footed at the exact moment trust matters most.

**Exit criteria:** a design partner can run their customer book through NeuronOS manually and get at least one correct "at risk" flag and one useful AI-drafted follow-up per week; **at least one automation has been run in `dry_run` mode against real data and its simulated output reviewed for accuracy before any automation is allowed to advance toward `live`; a first-pass AI unit-economics check (see `NeuronOS_Unit_Economics_Model.xlsx`) has been run against actual or estimated Phase 1 usage and compared to the intended price point, with no fatal margin problem found (or a plan in place if one is); a brand-new test organization can go from signup to a genuinely correct first AI Action within minutes using at least one of the three onboarding paths; and the team can recite the baseline security/liability answer (§17.7/§17.8) without needing to improvise it live.**

### Phase 2 — Connected Intelligence (Weeks 13–22)
This is where the "intelligence layer above your tools" promise becomes real.

- **Integrations v1:** Gmail, Google Drive, Google Calendar, **Outlook/Microsoft 365** (read-only ingestion) — contingent on provider review status from the Phase 2A track; sequence actual go-live by whichever provider's review clears first, not by product priority
- **Context Engine v1:** link customer ↔ email ↔ document ↔ meeting ↔ invoice
- **Projects module:** status, deadlines, risk flags, team, dependencies (UI spec + desktop mockup already delivered; **mobile/tablet mockups for the detail view are a required deliverable in this phase, not deferred further** — mobile-first approvals is a stated design principle and shouldn't fall behind on the two most-visited detail screens)
- **Meetings module:** calendar sync, pre-meeting briefs, auto-summarization from transcript/notes, action-item extraction (same mobile/tablet mockup requirement as Projects)
- **Decision Engine v1:** priority/urgency scoring across customers + projects + meetings combined; every score computation tagged with `score_algorithm_version` from day one (Database Spec §7.5) so this doesn't need retrofitting when the engine evolves in Phase 3
- **Automations builder:** custom trigger → condition → action flows (beyond canned templates); every automation created through the builder still starts in `dry_run` mode — the graduation path is not specific to the canned Phase 1 templates
- **Reports:** revenue trend, revenue-by-source, top customers — computed from live integrated data
- **Engineering requirement carried through this phase:** every new background job that talks to an external system (sync jobs, automation executions) must use the idempotency-key pattern established in Database Spec §7.4 — this is not optional for new integration work, since integration syncs are exactly the kind of job that gets retried on transient failures.

**Exit criteria:** disconnecting a design partner's spreadsheet-based workflow for a full week without losing anything they'd normally track.

### Phase 3 — Depth & Autonomy (Weeks 23–34)
- **Integrations v2:** Slack, WhatsApp Business, HubSpot/Salesforce/Zoho, QuickBooks/Zoho Books
- **Learning Engine:** incorporate approve/reject/edit signals to re-rank future AI Actions
- **AI Actions autonomy tiers:** low-risk actions (e.g., send reminder email) can move from "Approve" to "Auto with notify" per user preference
- **Advanced Reports:** cohort analysis, forecasting, team performance
- **Mobile app (React Native or PWA):** Pulse, approvals, chat
- **Voice command:** initial "Ask NeuronOS" voice input (as previewed in mockups)

### Phase 4 — Platform (Weeks 35+)
- Plugin/marketplace architecture for third-party and custom integrations
- Enterprise features: SSO, audit logs, granular permissions, data residency options
- Multi-model routing (OpenAI, Anthropic, Gemini, future local models) with cost/quality-based selection
- Public API for customers who want to build on NeuronOS

---

## 5. AI Architecture — Engine Specs

| Engine | Responsibility | MVP Implementation | Later Implementation |
|---|---|---|---|
| **Memory Engine** | Stores raw company knowledge (docs, emails, notes) | Postgres + pgvector, chunked embeddings | Add hierarchical summarization, retention/versioning policies |
| **Knowledge Engine** | Extracts entities (customers, projects, contracts, deadlines) | LLM extraction via structured output (JSON schema) on ingest | Fine-tuned extraction, confidence scoring, human-in-loop correction UI |
| **Context Engine** | Links entities into a relationship graph | Simple foreign-key relations in Postgres | Graph layer (e.g., Postgres + recursive CTEs, or dedicated graph store if scale demands) |
| **Decision Engine** | Scores risk/opportunity/priority/urgency | Rule-based scoring (recency, amount, sentiment keywords) | ML ranking model trained on Learning Engine signals |
| **Action Engine** | Generates emails, reports, tasks, follow-ups | LLM generation with templates + business context injection | Multi-step agentic execution (LangGraph) with tool use |
| **Learning Engine** | Learns from approvals/edits | Log approve/reject/edit deltas | Feed deltas into Decision Engine ranking + prompt refinement |

**Model routing:** start with a single primary model (Claude) for reasoning-heavy tasks (summaries, recommendations) and a cheaper/faster model for extraction and classification. Introduce the Model Router abstraction in Phase 2 so provider swaps don't touch application code.

**RAG pipeline (MVP):** document → chunk (semantic, ~500 tokens) → embed → pgvector store → retrieve top-k on query → inject into prompt with source citations.

---

## 6. Technology Stack (confirmed from blueprint)

**Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, TanStack Query, React Hook Form, Zod

**Backend:** FastAPI, Python 3.12, SQLAlchemy, Alembic, Celery, Redis

**Database:** PostgreSQL, pgvector, Redis (cache), Cloudflare R2 (file storage)

**AI:** LangGraph (orchestration), OpenAI + Anthropic Claude + Gemini (multi-model), Model Router abstraction, RAG, Business Context Engine

**Infra:** Docker, GitHub Actions, Railway (MVP), AWS (scale), Kubernetes (future), Prometheus + Grafana + Loki (observability), Sentry (errors)

**Decisions the team should lock down in Phase 0:**
- Monorepo (Turborepo/Nx) vs. separate frontend/backend repos
- Celery vs. a simpler task queue (e.g., Arq) if Celery/Redis ops overhead isn't justified pre-scale
- Whether pgvector is sufficient through Phase 2, or a dedicated vector DB (e.g., Qdrant) is needed once document volume grows

---

## 7. Data Model (v1 — core entities)

```
Organization
 ├── User (role: owner/admin/member)
 ├── Customer
 │    ├── Timeline Event (meeting, email, proposal, invoice, note)
 │    ├── Relationship Score (computed)
 │    └── Deal / Contract
 ├── Project
 │    ├── Task
 │    ├── Team Member (User ref)
 │    └── Risk Flag
 ├── Meeting
 │    ├── Attendee (Customer or User ref)
 │    ├── Summary (AI-generated)
 │    └── Action Item (→ Task)
 ├── Document
 │    ├── Chunk + Embedding
 │    ├── Tag
 │    └── Linked Entity (Customer/Project/Meeting — polymorphic)
 ├── Automation
 │    ├── Trigger
 │    ├── Condition
 │    └── Action
 ├── AI Action (suggested action: status = suggested/approved/rejected/executed)
 └── Integration Connection (provider, scopes, sync status)
```

Every entity that can be referenced by AI Actions or the Context Engine should carry: `id`, `organization_id`, `created_at`, `updated_at`, and a `source` field (manual vs. synced-from-integration) to support trust/audit needs later.

---

## 8. UI Module Specs — Projects & Meetings

These two modules are referenced in the blueprint's module list but weren't yet designed in the existing mockups. A matching high-fidelity mockup (`neuronos_projects_meetings.html`) has been delivered alongside this document — use it as the frontend build reference.

### 8.1 Projects
- **List view:** project name, client, status pill (On Track / At Risk / Needs Review / In Review), deadline, progress bar, team avatars
- **Filters/tabs:** All, At Risk, Due This Week, Completed
- **Stat row:** Total Projects, On Track, At Risk, Avg. Completion
- **Right rail — Project Intelligence:** AI summary of portfolio risk, Risks & Blockers list, one Recommended Action with a one-click draft/execute button
- **Detail view (not yet mocked — build next):** timeline, task list, dependency graph, linked documents/customers

### 8.2 Meetings
- **List view:** grouped by Today / Upcoming / Past / Needs Notes, time block, title, platform + duration + attendee count, status pill (Brief Ready / Upcoming / Summarized / Needs Notes)
- **Stat row:** Meetings Today, This Week, Action Items Created, Avg. Duration
- **Right rail — Meeting Intelligence:** next-meeting AI brief, talking points, action items from the most recent past meeting with checkboxes
- **Detail view (not yet mocked — build next):** full transcript/notes, recording link, all extracted action items with owner + due date, linked project/customer

Both modules reuse the shared shell: 220px sidebar, main content, 300px right intelligence rail — matching Pulse/Customers/Knowledge already built.

---

## 9. Security & Compliance Notes

- Per-organization data isolation at the database layer (row-level security or tenant_id scoping enforced in the ORM layer, not just app logic)
- OAuth scopes for each integration should be least-privilege and revocable per-user, with a visible "Disconnect" action (already designed in Settings mockup)
- AI Action execution logs must be retained (who approved, what was sent/changed, when) for auditability
- Document storage (Cloudflare R2) encrypted at rest; signed URLs with short expiry for access

---

## 10. Open Questions for the Team

1. Do we need a dedicated graph database before Phase 3, or does Postgres + CTEs hold up under real customer data volume?
2. What's the fallback UX when an integration sync fails silently — does Pulse show stale-data warnings?
3. What's the minimum bar (accuracy/precision) for the Decision Engine before we surface a risk score to a paying customer, and how do we message uncertainty in the UI?
4. Pricing/plan gating — which modules are Free vs. paid tiers, and does that affect module architecture (feature flags per org)?

---

## 11. Milestone Summary

| Phase | Duration | Outcome |
|---|---|---|
| Phase 0 | 4 weeks | Infra + design system ready; Google/Microsoft provider review submissions in flight |
| Phase 2A | Weeks 1–22 (parallel) | Integration provider reviews (Google, Microsoft, Salesforce, HubSpot, QuickBooks, Zoho, Slack, WhatsApp) progressing alongside all other phases — see §2A |
| Phase 1 | 8 weeks | MVP core usable manually, first design partners onboarded; automations ship dry-run-only; first unit-economics check done; cold-start onboarding path validated; reasoning/confidence + severity-gated confirmation shipped on every AI Action; baseline security/liability answer ready |
| Phase 2 | 10 weeks | Live integrations (contingent on Phase 2A review status), Projects + Meetings shipped (incl. mobile/tablet detail mockups), Context Engine live with a correction-loop review queue |
| Phase 3 | 12 weeks | Learning Engine, autonomy tiers, mobile, more integrations |
| Phase 4 | Ongoing | Platform: plugins, marketplace, enterprise, public API |

**Total to a genuinely "connected intelligence" product (end of Phase 2): ~22 weeks from kickoff — contingent on provider review timelines in §2A, which run on external schedules and are the most likely single point of delay outside the team's direct control.**

---

## Changelog

**v1.0 → v1.1 (gap-fix pass):** Added Phase 2A as an explicit parallel track for integration provider review (previously treated as engineering effort inside Phase 2's 10-week window — this was an underestimated timeline risk). Updated Phase 1's Automations scope to require dry-run/graduated-autonomy mode, resolving a contradiction with the "approve-first" philosophy. Added a first-pass AI unit-economics check to Phase 1 exit criteria, backed by the new `NeuronOS_Unit_Economics_Model.xlsx`. Added mobile/tablet detail-view mockups as a required Phase 2 deliverable rather than an indefinitely deferred one. Added an idempotency-key engineering requirement for all new background jobs from Phase 2 onward. Corresponding schema and API changes are in `NeuronOS_Database_Spec.md` and `NeuronOS_API_Spec.md`.

**v1.1 → v1.2 (this pass):** Added Onboarding as an explicit Phase 1 module deliverable addressing the cold-start activation risk, with Pulse's empty state redefined to show the onboarding path selector rather than a meaningless score. Added reasoning/confidence display and severity-gated confirmation to the Phase 1 AI Actions scope, addressing the "cried wolf" trust-calibration risk. Added a visible confidence/review-queue requirement to Phase 1 Knowledge module scope, addressing the missing Context Engine correction loop. Moved baseline security/liability readiness from an implicit Phase 4 assumption to an explicit Phase 1 requirement — not full SOC 2/DPA, but an honest, ready answer before any design partner connects real data. Corresponding schema/API changes are in the updated `NeuronOS_Database_Spec.md` and `NeuronOS_API_Spec.md`; the full security/liability content is in the new `NeuronOS_Trust_Security_FAQ.md`.
