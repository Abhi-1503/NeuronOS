# NeuronOS Master Blueprint

**Version:** 1.0
**Status:** Living document — source of truth for product, design, and engineering
**Owner:** Abhishek Singh
**Purpose of this document:** This is the single authoritative reference for what NeuronOS is, why it exists, and how it is built. Every other document (PRD, system architecture spec, UI spec, API reference, engineering standards) derives from this file and must not contradict it. Any AI coding assistant (Claude, Cursor, Windsurf, Devin, etc.) or new team member should read this file in full before generating product decisions, code, or design work.

> **Note on scope:** This v1 draft consolidates everything currently decided about NeuronOS into one coherent document, organized so it can be expanded chapter by chapter without restructuring. Sections marked **[EXPAND]** are the ones with the most room to grow into deeper implementation detail (e.g., full 200-endpoint API reference, per-screen specs for every screen, full database DDL) — these are natural next deliverables once this foundation is locked.

---

## Table of Contents

1. Executive Summary
2. Product Philosophy
3. Product Overview & Modules
4. User Journey
5. Module Specifications
6. Screen Inventory & UI Specification Standard
7. Interaction Model — "Every Button" Standard
8. Technical Philosophy (Why This Stack)
9. System Architecture
10. Backend Structure
11. Frontend Structure
12. Database Design
13. API Design Standard
14. AI Architecture (The Six Engines)
15. Coding Standards
16. Design Standards
17. Security & Compliance Standards
18. Roadmap
19. Long-Term Vision & Future Modules
20. Glossary

---

## 1. Executive Summary

### 1.1 What NeuronOS Is

NeuronOS is an AI-native business intelligence platform that operates as the intelligence layer above a company's existing software — not a replacement for it. A business today runs on some combination of Gmail, Google Drive, Slack, Microsoft Teams, HubSpot, Salesforce, Zoho, QuickBooks, Notion, calendars, and WhatsApp. Each of these tools stores information. None of them understands the business as a whole.

NeuronOS connects to these systems, continuously builds a live model of the business — its customers, projects, meetings, documents, and finances — and turns that model into prioritized, actionable recommendations. It does not ask the business owner to go looking for information. It tells them what needs attention, why, and what to do about it, and in many cases it can act directly (with approval).

### 1.2 Why NeuronOS Exists

Every company generates data. Almost none of that data becomes intelligence. A business owner today has to open ten different applications, mentally reconstruct the state of every customer relationship and project, and decide what to prioritize — every single day. This is slow, error-prone, and doesn't scale past a handful of people paying close attention.

Existing categories of software don't solve this:

- **CRMs** store customer records but require manual data entry and don't reason across projects, documents, or finances.
- **Project management tools** track tasks but have no idea whether a task is actually at risk of losing a customer.
- **AI chatbots** answer questions but have no persistent understanding of the business — every conversation starts from zero.
- **BI/reporting tools** visualize what already happened. They don't recommend what to do next.

NeuronOS's premise: the next generation of business software isn't a better dashboard — it's a system that understands the business the way a sharp Chief of Staff would, and tells the owner what matters before they have to ask.

### 1.3 Vision

Build the operating intelligence behind every modern business. NeuronOS becomes the default interface through which a business owner understands and operates their company — instead of opening ten applications every morning, they open NeuronOS.

### 1.4 Mission

Help every business make faster, better decisions through AI-powered business intelligence — by connecting the tools they already use, not replacing them.

### 1.5 Market Opportunity

Small and mid-sized businesses (the primary early target — see §1.7) are underserved by enterprise BI tools (built for large data teams, not solo founders or lean teams) and underserved by AI chatbot products (which have no durable memory of the business). This creates a gap for a product that is: (a) AI-native from the ground up, (b) integrates with tools SMBs already use rather than requiring migration, and (c) prioritizes recommended action over raw data display.

### 1.6 Product Summary

NeuronOS is a platform, not a single app. Its modules — Pulse, Memory/Knowledge, Customers, Projects, Meetings, Documents, AI Workspace, Automations, AI Actions, Reports, and Settings — all share one underlying AI core (see Chapter 14). A user can adopt one module (e.g., Customers) without needing the others, but the value compounds as more modules and more integrations are connected, because the Context Engine can link more of the business together.

### 1.7 Target Customers

- **Primary (MVP → Phase 2):** Founders and small teams (2–50 people) running service businesses, agencies, and early-stage SaaS companies — where the owner or a small ops team is currently doing manual cross-referencing across tools.
- **Secondary (Phase 3+):** Growing mid-market companies (50–250 people) with dedicated ops/RevOps functions who want a unifying intelligence layer across departmental tools.
- **Not the current target:** Large enterprises requiring deep customization, on-prem deployment, or industry-specific compliance (e.g., healthcare, finance) — these are explicitly out of scope until the Enterprise phase (Chapter 19).

### 1.8 Business Goals

- Prove the core loop (data in → context built → correct recommendation out) with a small number of design partners before scaling integrations.
- Reach a state where a design partner can safely stop manually tracking customer/project risk in a spreadsheet because NeuronOS catches it first.
- Build toward a usage-based or seat-based SaaS pricing model once core modules are stable (pricing model itself is a Phase 2/3 decision, not finalized in this document).

### 1.9 Success Metrics

Early-stage success is measured by trust and accuracy, not volume:

- **Recommendation precision:** % of AI Actions / risk flags that a user approves or acts on vs. dismisses as wrong.
- **Time-to-insight:** how quickly, after connecting a data source, NeuronOS surfaces a correct, non-obvious insight.
- **Reliance:** whether a design partner stops checking their old tools directly for the information NeuronOS now surfaces (the "did we replace the spreadsheet" test).
- **Retention of connected integrations:** whether users keep integrations connected over time (a proxy for perceived value vs. perceived risk).
- **AI cost as a share of price:** every LLM-backed feature has a real, usage-scaling cost — this needs to stay a bounded fraction of subscription price, not an afterthought discovered after customers are paying a fixed price. See `NeuronOS_Unit_Economics_Model.xlsx` for a working model with adjustable volume/pricing assumptions — this should be re-run against real design-partner usage data as soon as it exists, not treated as a one-time estimate.

Later-stage metrics (post-MVP) will include standard SaaS metrics — activation, retention, expansion revenue — once there's a stable paid product to measure.

### 1.10 Competitive Positioning

NeuronOS is not positioned against any single competitor category, because it doesn't sit in one category — it sits above several:

| Category | Example tools | What they do | What NeuronOS does differently |
|---|---|---|---|
| CRM | HubSpot, Salesforce | Store and manage customer records | Reasons across customers + projects + docs + finance, not just customer records |
| BI/Reporting | Looker, Metabase | Visualize historical data | Recommends forward-looking action, not just charts |
| AI chatbot | ChatGPT, generic copilots | Answer questions in the moment | Maintains persistent, continuously-updated business context |
| Automation | Zapier, Make | Trigger-based workflows | Automations are informed by business context and risk scoring, not just triggers |

NeuronOS's moat is not any single feature — it's the **Context Engine**: the accumulated, cross-referenced understanding of a specific business, which gets more valuable and harder to replicate the longer it runs.

### 1.11 Core Philosophy (Summary)

- We don't replace software. We connect it.
- We don't build dashboards. We build intelligence.
- AI recommends first. Automation (autonomous execution) comes later, and only once trust is earned.
- Every module shares one brain — no module reasons about the business in isolation.

(Full philosophy in Chapter 2.)

### 1.12 Long-Term Vision

Eventually NeuronOS becomes an AI Chief of Staff, AI Operations Manager, AI Sales Manager, AI Knowledge Manager, and AI Decision Engine — all through the same product surface. The end-state interaction model is not "where is the information" but "NeuronOS, what should we do today?" (Full detail in Chapter 19.)

---

## 2. Product Philosophy

### 2.1 We Don't Replace Software — We Connect It

Businesses have already invested time, money, and trust into their existing tools. Asking them to migrate off a CRM, an accounting system, or their email is a massive switching cost and a non-starter for most SMBs. NeuronOS's integration-first posture (read access via OAuth, later write access for automations) means adoption doesn't require ripping anything out. This is a deliberate strategic choice, not a limitation — it's what makes the product adoptable in week one rather than after a migration project.

### 2.2 We Don't Build Dashboards — We Build Intelligence

A dashboard answers "what is the current state." NeuronOS answers "what should happen next, and why." Where a traditional dashboard shows "Revenue: ₹24.6L," NeuronOS says "You're about to lose ₹8L because three enterprise customers haven't been contacted in 12 days." This distinction should shape every product decision: if a feature only displays data without a recommended next action, it is incomplete.

### 2.3 AI Recommends First, Automation Comes Later

Full autonomy (AI acting without human review) is a trust milestone, not a starting assumption. Every AI Action begins in a "Review → Approve" state. Only after a specific action type has a strong track record of correct suggestions for a specific organization should it become eligible for lower-friction execution (see AI Actions autonomy tiers, Chapter 18, Phase 3). This protects against the single biggest risk to the product: an AI system taking an embarrassing or costly wrong action on a business owner's behalf before it has earned the right to.

**Implementation rule (added after a documentation audit surfaced a contradiction between this philosophy and the shipped Automations UI):** this principle applies to *every* AI-initiated action, including ones configured through the Automations module — not just the ones that appear in the AI Actions queue by default. An automation toggled "Active" is still an AI-initiated action; it does not get a philosophy exemption just because it was set up once and then runs repeatedly. Concretely, every automation moves through three states before it can execute fully unsupervised:

1. **`dry_run`** — the automation is evaluated against real trigger conditions but nothing is sent; the user sees exactly what it *would have* done.
2. **`graduating`** — every real trigger creates a normal AI Action (review → approve), reusing the existing AI Actions queue rather than a separate mechanism.
3. **`live`** — only after a defined number of approved runs (default 5) does an automation execute without per-instance review — and any rejection during `graduating` resets that count, rather than being treated as a one-off exception.

This is now enforced at the schema level (`automations.mode`, `NeuronOS_Database_Spec.md` §6.1), not left as a design intention that the implementation can silently ignore.

### 2.4 Why Chat-First

A chat interface (AI Workspace) is the fallback for anything the structured UI doesn't yet anticipate. Structured screens (Pulse, Customers, Projects) handle the 80% of interactions that are predictable and repeated; chat handles the long tail — ad hoc questions, unusual requests, exploratory analysis — without requiring a new UI to be built for every possible question.

### 2.5 Why Minimal, Calm UI

The product's job is to reduce the number of things a business owner has to actively track. A UI that is visually loud, dense, or attention-grabbing works against that goal. Design references (Apple's restraint, Linear's information density done cleanly, Notion's calm content-first layout) are directional inspirations for *how* things should feel, not literal style to copy — see Chapter 16 for the actual design system derived from these principles.

### 2.6 One AI Core, Many Surfaces

Every module reads from and writes to the same six engines (Memory, Knowledge, Context, Decision, Action, Learning — Chapter 14). No module should implement its own bespoke "intelligence" that the others can't benefit from. If the Customers module gets better at scoring relationship risk, that improvement should be available to the Decision Engine when it scores overall business risk in Pulse. This is the single most important architectural constraint in the whole system.

### 2.7 Show Reasoning, Not Just Conclusions

**Added after a documentation audit surfaced a real trust risk (Strategic Gap Analysis §3.2):** the MVP Decision Engine is explicitly rule-based (recency, amount, keyword signals — see Chapter 14), and rule-based scoring will produce false positives. Unlike a typical SaaS feature, an incorrect insight here doesn't just cost a user a few minutes — it costs trust in every subsequent insight, because the entire value proposition is "trust what it tells you." The first time NeuronOS says "you're about to lose ₹8L" and the business owner knows that's wrong, the product's core premise is damaged for that user, possibly permanently.

**The mitigation is architectural, not cosmetic:** every AI-generated risk flag or recommendation must show its reasoning — the actual signal that produced the conclusion (e.g., "No timeline event logged for 12 days; last 3 emails went unanswered; deal stage hasn't advanced in 18 days") — displayed next to the conclusion, not hidden behind an optional "why?" click. Where the generating engine can produce one, a confidence score is shown alongside it. This reframes a wrong call from "an unexplained, overconfident claim" into "here's the signal I saw — was I right?", which is a fundamentally more forgivable failure mode for a young product's inevitable mistakes. This is now enforced at the schema level (`ai_actions.reasoning`/`confidence_score`, `risk_flags.reasoning`/`confidence_score` — `NeuronOS_Database_Spec.md` §7.1/§3.4) and at the API level (both fields are always present in the relevant responses, with an explicit note that the frontend must render them visibly — `NeuronOS_API_Spec.md` §7).

---

## 3. Product Overview & Modules

NeuronOS is composed of the following modules. Each is detailed further in Chapter 5.

| Module | One-line purpose |
|---|---|
| **Pulse** | Daily executive briefing — business health, today's priorities, AI recommendations |
| **Memory / Knowledge** | Company-wide knowledge base — documents, SOPs, contracts, emails, notes, all searchable and AI-summarized |
| **AI Workspace** | Chat-first interface for ad hoc questions, drafting, and analysis over the business's full context |
| **Customers** | Relationship intelligence — beyond CRM record-keeping, includes AI summaries, risk scores, and recommended next actions per customer |
| **Projects** | Delivery tracking — status, risk, deadlines, dependencies, team |
| **Meetings** | Meeting lifecycle — pre-meeting briefs, auto-summarization, action item extraction |
| **Documents** | Every document becomes searchable, summarized, tagged, and linked to the customers/projects/meetings it relates to |
| **Automations** | Trigger → condition → action workflows, informed by business context |
| **AI Actions** | The queue of AI-suggested actions awaiting review, approval, or delegation |
| **Reports** | Analytics — revenue, deals, risk, team performance |
| **Settings** | Org/team management, integrations, preferences, billing |

Future/platform-phase modules — **Marketplace**, **Plugins**, **Enterprise** — are covered in Chapter 19 and are explicitly out of scope until Phase 4.

---

## 4. User Journey

### 4.1 Primary Daily Journey (Business Owner / Manager)

```
Morning
  ↓
Login
  ↓
Pulse (Business Health score, Today's Focus cards, AI Insight of the day)
  ↓
Review AI Actions queue → Approve / Review / Delegate
  ↓
AI Workspace (ask a follow-up question, draft something, dig into a flagged risk)
  ↓
Work happens elsewhere in the product as needed:
   → Customers (check an at-risk account)
   → Projects (check a blocked delivery)
   → Meetings (review today's briefs, join a call)
  ↓
Notifications throughout the day (new risk detected, action completed, integration issue)
  ↓
End of day: Reports / Daily Summary
  ↓
Logout
```

### 4.2 What Happens at Each Step (System Behavior)

- **Login:** auth check → org context loaded → Decision Engine's overnight batch run is already reflected in Pulse (no on-demand recompute needed for the daily score).
- **Pulse load:** Business Health score (computed), Today's Focus cards (top-N items from Decision Engine ranked by urgency × impact), AI Insight card (single highest-priority narrative insight, e.g. "you're about to lose ₹X").
- **Approve/Review AI Action:** user decision is logged (Learning Engine input) → if approved, Action Engine executes (e.g., sends an email) → result logged → relevant module (Customers/Projects) updated → notification confirms completion.
- **AI Workspace query:** RAG retrieval over Knowledge Engine + Context Engine relationship graph → LLM generates response with citations back to source documents/records.
- **End of day summary:** batch-generated narrative summarizing what changed, what was completed, what's still outstanding — not just a re-display of Pulse.

### 4.3 Secondary Journeys

- **New team member onboarding:** invited → role assigned (Owner/Admin/Member) → sees only the modules/data their permissions allow (see §17.1 RBAC).
- **First-time setup (no integrations yet):** user can still use Customers, Projects, Documents manually — the product must be valuable with zero integrations connected (this is an MVP hard requirement, not a nice-to-have).
- **Integration connection flow:** Settings → Integrations → OAuth consent → initial sync (background job) → Knowledge/Context Engines begin ingesting → user notified when initial sync completes.

### 4.4 Cold-Start Onboarding Journey

**Gap addressed:** Pulse, the AI Workspace, and Customer risk scoring all depend on data already being in the system. A brand-new organization with zero uploaded documents and zero connected integrations has nothing for the AI to reason about — Pulse would show an empty or meaningless Business Health score on day one. This was flagged as the single biggest activation risk in the Strategic Gap Analysis (§3.1), with no onboarding flow designed to address it. Full detail is in the companion document `NeuronOS_Onboarding_Spec.md`; this section establishes the principle and the three supported paths.

**Principle:** a new organization must reach one genuinely correct, non-generic insight within minutes of signing up — not after a "full sync" that can take hours, and not only after every module has been populated. Three equally-valid entry points are offered, and the user picks whichever fits how they already have information organized — this is a deliberate choice not to force one canonical path:

```
Sign up
  ↓
"How do you want to get started?" (pick one — can add the others later)
  ├── Connect one integration (e.g., Gmail) → initial sync of recent emails only (not full history)
  ├── Upload your top 3–5 key documents (contracts, proposals, a customer list)
  └── Manually add your top 5 customers (name + last contact date is enough to start)
  ↓
Within minutes: NeuronOS surfaces one real, specific insight from whatever was just provided
   (e.g., "You added XYZ Solutions — I don't see any contact in the last 12 days. Want me to draft a check-in?")
  ↓
This becomes the org's first AI Action — approving or dismissing it is the user's first real interaction
with the trust loop described in §2.7, on real data they recognize, not a demo
  ↓
Prompted (not forced) to add the next data source to deepen the picture
```

**What this changes about the rest of the product:** Pulse's empty state (an org with `onboarding_completed_at IS NULL`) must never render a blank or meaningless Business Health score — it should render the onboarding path selector directly, treating onboarding as Pulse's actual first-run content rather than a separate wizard the user has to get through before "the real product" appears. `organizations.onboarding_method` and `onboarding_first_insight_at` (`NeuronOS_Database_Spec.md` §1.3) track which path was taken and when the milestone was hit — the latter is also the "time-to-insight" success metric from §1.9, made measurable per organization rather than only estimated in aggregate.

---

## 5. Module Specifications

For each module: Purpose, Core Features, Primary Users, Permissions Model, Database Dependency, AI Engine Dependency, Cross-Module Dependencies.

### 5.1 Pulse

- **Purpose:** Single-glance daily briefing; the "front door" of the product.
- **Features:** Business Health score, Today's Focus (ranked action cards), AI Insight narrative, Daily/Weekly Summary, quick-ask chat box.
- **Users:** All roles, but content is scoped to what each role can see (a Member sees their assigned items; an Owner sees org-wide).
- **Permissions:** Read-only view of aggregated data; approving an AI Action from Pulse requires the same permission as approving it from AI Actions directly.
- **Database dependency:** Reads from Customer, Project, Meeting, AI Action, Automation tables — writes nothing directly (all writes happen through the modules an action targets).
- **AI dependency:** Decision Engine (scoring/ranking), Action Engine (drafting the narrative insight).
- **Cross-module dependency:** Effectively depends on every other module having current data; is the most sensitive module to staleness or integration sync failure (see open question in §18, Roadmap doc).

### 5.2 Memory / Knowledge

- **Purpose:** Company-wide knowledge base that makes every document, note, and policy searchable and usable by the AI.
- **Features:** Upload (PDF/DOCX/etc.), auto-tagging, AI summary per document, semantic search, linking to related customers/projects/meetings.
- **Users:** All roles; Admins can set document-level visibility.
- **Permissions:** Document visibility can be restricted per-team or per-role (e.g., a contract only visible to Owner/Admin).
- **Database dependency:** Document, Chunk/Embedding, Tag, Linked Entity tables.
- **AI dependency:** Memory Engine (storage/embedding), Knowledge Engine (entity extraction on ingest).
- **Cross-module dependency:** Feeds AI Workspace's RAG retrieval; feeds Context Engine's entity linking.

### 5.3 AI Workspace

- **Purpose:** Conversational interface for anything not covered by a structured screen.
- **Features:** Multi-turn chat, source citations, saved chat history, quick-action buttons (e.g., "Draft proposal for X").
- **Users:** All roles.
- **Permissions:** Answers are scoped to what the asking user is permitted to see — the chat must never surface data across a permission boundary just because it's in the same knowledge base.
- **Database dependency:** Reads across nearly all entities; writes Chat/Message history.
- **AI dependency:** All six engines are reachable from here — this is the most AI-dependency-heavy module.

### 5.4 Customers

- **Purpose:** Relationship intelligence beyond record-keeping.
- **Features:** Timeline (all interactions), AI Summary, Relationship Score, Revenue prediction, Contract status, Recommended Next Action.
- **Users:** Sales/account roles primarily; visible org-wide by default (permission-gated per org policy).
- **Database dependency:** Customer, Timeline Event, Deal/Contract tables.
- **AI dependency:** Decision Engine (Relationship Score, risk flagging), Action Engine (drafting follow-ups).
- **Cross-module dependency:** Links to Projects (delivery for this customer), Meetings (interaction history), Documents (contracts/proposals).

### 5.5 Projects

- **Purpose:** Delivery tracking with risk awareness.
- **Features:** Status, deadline, progress, team, dependencies, risk flags. (Full UI spec delivered separately — see companion mockup file.)
- **Users:** Delivery/ops roles; team members see projects they're assigned to, Admins/Owners see all.
- **Database dependency:** Project, Task, Team Member ref, Risk Flag tables.
- **AI dependency:** Decision Engine (risk/priority scoring), Context Engine (linking project to customer/meetings).
- **Cross-module dependency:** Feeds Pulse's Today's Focus when a project risk crosses a threshold.

### 5.6 Meetings

- **Purpose:** Full meeting lifecycle — before, during, after.
- **Features:** Calendar sync, pre-meeting AI brief, auto-summarization, action item extraction (which become Tasks). (Full UI spec delivered separately.)
- **Users:** All roles who attend meetings.
- **Database dependency:** Meeting, Attendee, Summary, Action Item tables.
- **AI dependency:** Action Engine (summarization, brief generation), Knowledge Engine (extracting entities mentioned in the meeting).
- **Cross-module dependency:** Action items become Tasks in Projects; briefs pull from Customers and Documents.

### 5.7 Documents

- **Purpose:** Every uploaded or synced file becomes structured knowledge, not just storage.
- **Features:** Search, AI summary, tagging, linking to entities.
- **Overlap note:** Documents is the storage/management layer; Memory/Knowledge is the AI reasoning layer over the same underlying files. In practice these are presented as one module ("Knowledge") in the current UI — this document treats them as one for implementation purposes.

### 5.8 Automations

- **Purpose:** Encode repetitive workflows as trigger → condition → action.
- **Features (MVP):** canned templates (follow-up if no reply, invoice overdue reminder, welcome new client, feedback request).
- **Features (Phase 2+):** custom automation builder.
- **Users:** Admins configure; effects are visible to all relevant roles.
- **Database dependency:** Automation, Trigger, Condition, Action tables.
- **AI dependency:** Decision Engine (deciding when a condition is "met" if it's not a hard rule, e.g. "customer seems unhappy"), Action Engine (executing the action).

### 5.9 AI Actions

- **Purpose:** The queue where every AI-suggested action across the whole product surfaces for human review.
- **Features:** Suggested / Approved / Rejected / Delegated / Executed states; filters (Suggested for you, All, Completed, Delegated); every action shows its `reasoning` and `confidence_score` inline (§2.7); actions with `severity_tier = 'high'` (e.g., sending a contract email, generating an invoice) require an explicit secondary confirmation rather than a single-click approve, distinct visually — not just functionally — from low-severity actions (Strategic Gap Analysis §3.4, Database Spec §7.1).
- **Permissions:** A user can only approve actions within their permission scope (e.g., a Member can't approve an action that sends an email on the Owner's behalf unless delegated).
- **AI dependency:** Every engine feeds into this queue; Learning Engine consumes the approve/reject/edit signal from here.

### 5.10 Reports

- **Purpose:** Analytics on revenue, deals, risk, and team performance.
- **Features (MVP):** static overview computed from available data (manual or integrated).
- **Features (Phase 2+):** live computation from integrated data sources, trend charts, cohort analysis.

### 5.11 Settings

- **Purpose:** Org and account administration.
- **Features:** Company profile, team management, integrations (connect/disconnect), billing, notification preferences, danger zone (delete account, disconnect all integrations).
- **Permissions:** Owner-only for billing and account deletion; Admin+ for team/integration management.

---

## 6. Screen Inventory & UI Specification Standard

### 6.1 Confirmed Screens (mockups exist)

Pulse (Home), Customers (list + detail), Knowledge (hub + document view), AI Actions, Automations, Reports, Settings — all confirmed via existing high-fidelity mockups.

### 6.2 Newly Specified Screens

Projects (list view) and Meetings (list view) — specified and mocked in this workstream (see companion HTML mockup). Their **detail views** (Project detail, Meeting detail) are the next screens to design — flagged as open work in §18.

### 6.3 Per-Screen Documentation Standard **[EXPAND]**

Every screen, when fully specified, should be documented against this template (this is the standard referenced in the original planning conversation — applying it in full to all ~15 screens is a follow-on deliverable, not done exhaustively in this v1):

- Purpose & user goal
- Components & layout (desktop / tablet / mobile)
- States: default, loading, error, empty
- Animations & transitions
- AI interaction points (what's AI-generated vs. static)
- Accessibility notes (keyboard nav, screen reader labels, contrast)
- Business logic triggered by this screen
- API calls made on load and on each user action
- Permissions (what's hidden/disabled per role)
- Acceptance criteria
- Edge cases

### 6.4 Shared Shell (applies to all screens)

220px left sidebar (nav + Business Health card + user row) → main content area → 300px right "intelligence" rail (AI summary, insights, recommended action) where applicable. This shell is fixed across Pulse, Customers, Knowledge, Projects, and Meetings — new screens should not deviate from it without a specific reason documented in the design review.

---

## 7. Interaction Model — "Every Button" Standard

Every interactive element that triggers a backend effect should be traceable end-to-end. Standard trace format, illustrated with the "Approve" button on an AI Action:

```
User clicks Approve
  ↓
Frontend: optimistic UI update (card moves to "Approved")
  ↓
API: POST /ai-actions/{id}/approve
  ↓
Backend: permission check → status update → enqueue execution job
  ↓
Action Engine: executes the underlying action (e.g., send email via Gmail integration)
  ↓
Database: AI Action status → "executed"; execution log written
  ↓
Learning Engine: approval signal recorded
  ↓
Notification: user notified of completion (or failure, with retry option)
  ↓
Analytics: event logged for success-rate tracking
```

This is the standard every meaningfully-interactive button in the product should be able to be traced against. Applying it exhaustively to every button in every screen is a follow-on deliverable **[EXPAND]**.

---

## 8. Technical Philosophy (Why This Stack)

| Choice | Why |
|---|---|
| **Next.js 15 / React 19** | Server components reduce client bundle for a content-and-data-heavy app; mature ecosystem; team familiarity assumed. Considered and rejected: Angular (heavier, less suited to the rapid iteration needed pre-PMF). |
| **TypeScript** | Type safety across a large, multi-module app where entities (Customer, Project, Meeting) are shared across many screens — reduces cross-module integration bugs. |
| **Tailwind + shadcn/ui** | Consistent design tokens without a heavyweight design-to-code pipeline; shadcn's copy-in-component model keeps full control over styling, important for the "calm, distinctive" UI goal (Chapter 16). |
| **FastAPI / Python 3.12** | Python is the natural choice given the AI-heavy backend (LangGraph, embeddings, model SDKs are Python-first); FastAPI gives async support and automatic OpenAPI docs, which matters for a 100+ endpoint surface. Considered and rejected: Node backend (would fragment the stack across two languages for AI-heavy logic without a clear benefit). |
| **PostgreSQL + pgvector** | One database for both relational business data (customers, projects) and vector embeddings (documents) — avoids operating two data stores in MVP. Revisit (per open question in the roadmap doc) once document volume or query latency demands a dedicated vector DB. |
| **Redis** | Caching + Celery broker; justified by need for background job processing (syncs, AI Action execution) from day one. |
| **LangGraph** | Orchestration for multi-step agentic flows (e.g., Action Engine drafting → checking → finalizing) rather than hand-rolled prompt chaining. |
| **Multi-model (Claude / OpenAI / Gemini) via Model Router** | No single model is optimal for every task (cheap classification vs. expensive reasoning); the Model Router abstraction (Phase 2) avoids locking application code to one provider. |
| **Docker / Railway (MVP) → AWS + Kubernetes (scale)** | Railway minimizes DevOps overhead pre-PMF; migration path to AWS/K8s is deferred until scale actually requires it, not built prematurely. |

---

## 9. System Architecture

```
                     ┌─────────────────────────┐
                     │      Business Owner      │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │   Frontend (Next.js)     │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │     API Gateway (FastAPI)│
                     └────────────┬────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼───────┐        ┌────────▼────────┐        ┌───────▼───────┐
│  Core Services │        │   AI Core Engines │        │  Integrations  │
│ (Customers,    │◄──────►│ (Memory, Knowledge,│◄──────►│ (Gmail, Slack, │
│  Projects,     │        │  Context, Decision,│        │  CRM, etc.)    │
│  Meetings, ...)│        │  Action, Learning) │        │                │
└───────┬───────┘        └────────┬────────┘        └───────┬───────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │   PostgreSQL + pgvector  │
                     │   Redis (cache/queue)    │
                     │   Cloudflare R2 (files)  │
                     └─────────────────────────┘
```

Core services and AI engines are deliberately drawn as peers, not as core-services-calling-AI-as-a-utility — this reflects the philosophy in §2.6 that intelligence isn't bolted onto modules, it's shared infrastructure they're built on top of.

### 9.1 Integration Review & Compliance Lead Times (a real architectural constraint, not just a legal footnote)

**Gap addressed:** the original roadmap treated "connect Gmail/Drive/Calendar/CRM" as pure engineering effort, sized entirely by how long the integration code takes to write. In reality, every provider with meaningful data access runs its own external app-review process, on its own schedule — and for the more sensitive scopes NeuronOS needs, that process is not fast:

| Provider | Review mechanism | Why it matters here |
|---|---|---|
| **Gmail / Google Workspace** | OAuth verification for sensitive scopes; **CASA (Cloud Application Security Assessment)** for restricted scopes (full mailbox access) | Full mailbox access is a restricted scope — this requires a third-party security assessment, not just a Google support ticket, and needs **annual re-verification** once approved. This is the single longest lead time in the integration list if the broadest scope is requested. |
| **Google Drive / Calendar** | Same Google verification pipeline as above, scope-dependent | Narrower scopes (e.g., specific file access, read-only calendar) may sit in a lighter review tier — worth designing around deliberately (see Database Spec §8.1's scope-minimization note). |
| **Outlook / Microsoft 365** | Microsoft identity platform app registration + admin consent flow; Graph API permissions above a certain sensitivity require **publisher verification** and, for multi-tenant apps distributed broadly, Microsoft's own app compliance review | A separate process from Google's, with its own timeline and its own scope-classification logic — cannot be batched with the Google work. |
| **Salesforce** | AppExchange Security Review (if listing) or a direct customer-specific connected-app review | Known for being a slow, multi-cycle review even for experienced ISVs; budget generously. |
| **HubSpot** | App certification / marketplace review process | Functional review plus scope justification, similar in spirit to Google's but a separate submission. |
| **QuickBooks (Intuit)** | Developer review to move from sandbox keys to production keys, with extra scrutiny given financial data | Financial-data access tends to draw closer review than calendar/email access. |
| **Zoho (CRM / Books)** | Zoho's own developer/partner review for OAuth client approval | Generally lighter-weight than the above, but still an external dependency, not a same-day approval. |
| **Slack / WhatsApp Business** | Slack app review (lighter); WhatsApp Business API requires **Meta Business verification and message template approval**, with per-conversation costs | WhatsApp in particular is meaningfully higher-friction than a typical OAuth integration — treat it as its own workstream, not a checkbox alongside Slack. |

**What this changes about the plan:**

1. **These review processes should start as early as an OAuth consent screen and a working demo exist — in parallel with Phase 1 development, not as a Phase 2 dependency that begins after the integration code is "done."** The phase doesn't finish when the code is finished; it finishes when the slowest external reviewer says yes.
2. **Sequence submission order by review difficulty, not by product priority.** If Gmail's CASA assessment has the longest lead time, start that process first regardless of which module is being actively built.
3. **Scope minimization is a genuine design lever, not just a compliance nicety** — a narrower requested scope can mean a materially lighter review tier. This should be revisited explicitly for Gmail/Drive before submission (see Database Spec §8.1).
4. **Annual re-verification for restricted-scope integrations is an ongoing operating cost**, not a one-time Phase 2 line item — someone needs to own this every year, and it should be budgeted as recurring, not forgotten once the first approval lands.
5. **The Roadmap's Phase 2 timeline (§18) has been updated** to reflect provider review as a parallel track starting in Phase 0/1, rather than sequential engineering effort inside the 10-week Phase 2 window — see `NeuronOS_Roadmap_Spec.md`.

### 9.2 Reliability Targets (SLOs)

**Gap addressed:** Sentry and Prometheus/Grafana/Loki were named as observability tools with no stated target for what "working well enough" means — without a target, there's no way to know if the system is meeting the bar or silently degrading.

Initial SLO targets (to be revisited once real usage data exists — these are starting hypotheses, not measured commitments to customers yet):

| Surface | Target | Rationale |
|---|---|---|
| Pulse page load (excluding AI Summary) | p95 < 800ms | Pulse is the "front door" — Blueprint §2.5's calm-UI philosophy is undermined by a slow front door |
| API read endpoints | p95 < 300ms | Standard REST responsiveness bar |
| API write endpoints | p95 < 600ms | Slightly more headroom for validation + DB writes |
| Integration sync staleness | Flagged to user if `last_synced_at` > 2 hours (email/calendar) or > 24 hours (CRM/accounting) | See Database Spec §7.6 — this is the resolution to the Roadmap's "stale data warning" open question |
| Platform uptime | 99.5% (MVP) → 99.9% (post-Phase 2) | Deliberately modest at MVP — an aggressive early SLA is a promise the team can't yet back operationally |
| AI generation endpoints (chat, drafting) | p95 < 6s to first meaningful content | Generation is inherently slower; streaming (API Spec open item) matters more here than raw latency |

These targets should be wired into the Prometheus/Grafana setup as actual dashboards and alerts once Phase 0 infrastructure is in place — naming a target and never measuring against it is equivalent to not having one.

---

## 10. Backend Structure

Proposed folder structure (FastAPI):

```
backend/
├── app/
│   ├── api/                # route definitions, versioned (v1/)
│   ├── core/                # config, security, dependency injection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # business logic per module (customers, projects, ...)
│   ├── ai/                   # the six engines, model router, prompt library
│   ├── integrations/         # per-provider connectors (gmail, slack, hubspot, ...)
│   ├── workers/               # Celery tasks (sync jobs, action execution, embeddings)
│   └── repositories/           # data access layer, separated from services for testability
├── alembic/                   # migrations
└── tests/
```

Patterns: **repository pattern** for data access (keeps services testable without hitting the DB), **service layer** per module (keeps route handlers thin), **event-driven** internal notifications (e.g., "customer risk score changed" event triggers a Pulse recompute) to avoid tight coupling between modules — detailed event/queue design is a follow-on deliverable **[EXPAND]**.

---

## 11. Frontend Structure

```
frontend/
├── app/                 # Next.js app router, one route group per module
├── components/
│   ├── ui/                # shadcn primitives
│   ├── shared/             # shell (sidebar, right rail), shared cards, pills
│   └── modules/             # module-specific components (customer-card, project-row, ...)
├── lib/                  # API client, query hooks (TanStack Query), utils
├── hooks/
└── styles/                # Tailwind config, design tokens
```

Design tokens (colors, type scale, spacing) should live in one place (`styles/tokens`) and be the single reference for both this repo and any future mockup work, so mockups and shipped code never drift — see Chapter 16.

---

## 12. Database Design

### 12.1 Core Entity Relationship (v1)

```
Organization
 ├── User (role: owner/admin/member)
 ├── Customer
 │    ├── Timeline Event
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
 │    └── Linked Entity (polymorphic: Customer/Project/Meeting)
 ├── Automation
 │    ├── Trigger
 │    ├── Condition
 │    └── Action
 ├── AI Action (status: suggested/approved/rejected/executed)
 └── Integration Connection (provider, scopes, sync status)
```

### 12.2 Cross-Cutting Column Standard

Every entity carries: `id` (UUID), `organization_id` (tenant scoping), `created_at`, `updated_at`, `source` (manual vs. synced-from-integration — important for trust/audit), and a `deleted_at` (soft delete, to support recovery — see §12.3).

### 12.3 Lifecycle & Recovery Standard

Default deletion strategy across all entities is **soft delete** (`deleted_at` timestamp) with a recovery window (default 30 days) before hard deletion, except where a user explicitly invokes a "permanent delete" action (e.g., Settings → Danger Zone → Delete Account). Full per-table lifecycle detail (retention policy per entity type, cascade rules) is a follow-on deliverable **[EXPAND]**.

### 12.4 Indexing & Performance Notes

- `organization_id` should be the leading column in composite indexes for all tenant-scoped tables (supports row-level security and query performance together).
- Vector similarity search (pgvector) on `Chunk.embedding` should be indexed with an approximate nearest-neighbor index (e.g., HNSW) once chunk volume passes the point where sequential scan becomes slow — exact threshold to be determined empirically, not assumed upfront.

### 12.5 Score & Algorithm Versioning

**Gap addressed:** the Business Health Score and Relationship Score are both expected to move from rule-based (MVP) to ML-based (Phase 3+) implementations over time. Without versioning, a historical trend chart can't distinguish "the business actually changed" from "we changed how we measure it." Every score-bearing entity now carries a `score_algorithm_version` field, and score history is retained in an append-only `score_history` table rather than only the latest cached value — full detail in `NeuronOS_Database_Spec.md` §7.5. Any UI rendering a score trend over time should visually mark the point where the algorithm version changes.

Full DDL, per-table constraints, and audit logging design are follow-on deliverables **[EXPAND]**.

---

## 13. API Design Standard

### 13.1 Conventions

- REST, versioned under `/api/v1/`.
- Resource-oriented URLs (`/customers/{id}`, `/projects/{id}/tasks`), actions as sub-resources or verbs where REST purity would be awkward (`/ai-actions/{id}/approve`).
- Auth: bearer token (session or API key for future public API), every request scoped to `organization_id` derived from the token — never accepted as a client-supplied parameter.
- Standard error envelope: `{ "error": { "code": "...", "message": "...", "details": {...} } }`.
- Rate limiting per organization and per endpoint category (read vs. write vs. AI-generation endpoints, which are more expensive).

### 13.2 Per-Endpoint Documentation Template

Every endpoint, when fully specified, is documented as: Purpose, Headers, Request Body, Validation Rules, Response Schema, Error Cases, Required Permissions, Example Request/Response, Rate Limit, Security Notes.

### 13.3 Endpoint Inventory (representative, not exhaustive)

| Resource | Key endpoints |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `POST /auth/invite` |
| Customers | `GET/POST /customers`, `GET/PATCH/DELETE /customers/{id}`, `GET /customers/{id}/timeline` |
| Projects | `GET/POST /projects`, `GET/PATCH /projects/{id}`, `GET/POST /projects/{id}/tasks` |
| Meetings | `GET/POST /meetings`, `GET /meetings/{id}/brief`, `POST /meetings/{id}/summarize` |
| Documents | `POST /documents` (upload), `GET /documents/{id}`, `GET /documents/search` |
| AI Actions | `GET /ai-actions`, `POST /ai-actions/{id}/approve`, `POST /ai-actions/{id}/reject` |
| Automations | `GET/POST /automations`, `PATCH /automations/{id}` |
| AI Workspace | `POST /chat/messages` |
| Integrations | `GET /integrations`, `POST /integrations/{provider}/connect`, `DELETE /integrations/{provider}` |

Full ~200-endpoint reference (all CRUD + action endpoints across every module, documented to the §13.2 standard) is the largest single follow-on deliverable **[EXPAND]** — recommend generating this module-by-module rather than all at once.

---

## 14. AI Architecture (The Six Engines)

| Engine | Responsibility | MVP Implementation | Later Implementation |
|---|---|---|---|
| **Memory Engine** | Stores raw company knowledge | Postgres + pgvector, chunked embeddings | Hierarchical summarization, retention/versioning |
| **Knowledge Engine** | Extracts entities from raw content | LLM structured-output extraction on ingest | Confidence scoring, human correction UI |
| **Context Engine** | Links entities into a relationship graph | Foreign-key relations in Postgres; low-confidence AI-inferred links surface in a review queue for user confirm/reject rather than being trusted at full weight (see §14.1 below) | Dedicated graph layer if scale demands |
| **Decision Engine** | Scores risk/opportunity/priority/urgency | Rule-based scoring (recency, amount, keywords) | ML ranking model trained on Learning Engine signal |
| **Action Engine** | Generates emails, reports, tasks, follow-ups | LLM generation with templates + context injection | Multi-step agentic execution via LangGraph with tool use |
| **Learning Engine** | Learns from approvals/edits | Log approve/reject/edit deltas | Feed into Decision Engine ranking + prompt refinement |

### 14.1 Context Engine Correction Loop

**Gap addressed:** the Context Engine's inferred links (document ↔ customer, etc.) had a confidence score but no way for a human to correct a wrong one — meaning an error here would silently propagate into every downstream engine that relies on it (Decision, Action), since both trust the Context Engine's graph without question. This was flagged as a real gap between the database design and the product surface (Strategic Gap Analysis §3.3).

- Every AI-inferred link (`linked_entities` — Database Spec §5.4) carries a `status` (`ai_suggested`/`confirmed`/`rejected`/`manual`) alongside its `confidence` score.
- Links below a configurable confidence threshold (default 0.7) surface in a review queue (`GET /linked-entities/review-queue`) rather than only existing invisibly in the background.
- **Downstream engines must not weight a low-confidence, unconfirmed link the same as a confirmed or manually-created one** — this is a hard rule, not a tuning suggestion, since it's the actual mechanism that prevents a single shaky inference from silently driving a customer's risk score before any human has looked at it.
- Rejecting a link is a Learning Engine signal too — a consistently wrong inference pattern (e.g., always mis-linking documents by company name substring match) should surface as a Knowledge Engine quality issue worth fixing at the source, not just repeatedly corrected one link at a time.

### 14.2 RAG Pipeline (MVP)

Document → semantic chunking (~500 tokens) → embed → store in pgvector → retrieve top-k on query → inject into prompt with source citations back to the originating document.

### 14.3 Model Routing

MVP: single primary model for reasoning-heavy tasks (summaries, recommendations), a cheaper/faster model for extraction and classification. Phase 2 introduces the Model Router abstraction so provider swaps (or per-task model selection) don't touch application code.

### 14.4 Prompt Library & Agent System

A versioned prompt library (per engine, per task type) should live in `backend/app/ai/prompts/` with each prompt template tested against a small golden-set of inputs before being changed — this prevents silent regressions when a prompt is "improved" for one case but breaks another. Full prompt library content and agent-system design (multi-step LangGraph flows for Action Engine) is a follow-on deliverable **[EXPAND]**.

---

## 15. Coding Standards

- **Naming:** descriptive, domain-language names (`RelationshipScore`, not `score1`); consistent casing (`snake_case` Python, `camelCase` TypeScript).
- **Folder structure:** one module = one folder, mirrored between frontend and backend where possible (`customers/` in both).
- **Git:** conventional commits (`feat:`, `fix:`, `chore:`), feature branches off `main`, PR review required before merge.
- **Testing:** unit tests for services/business logic, integration tests for API endpoints, minimum coverage threshold to be set once test infra is in place (not fixed arbitrarily here).
- **Logging:** structured logs (JSON) with `organization_id` and `request_id` on every log line for traceability.
- **Errors:** never swallow exceptions silently; every AI Action execution failure must surface to the user, not just to logs.
- **No placeholder code in shipped PRs** — a stub is acceptable in a draft PR but must be flagged explicitly, not merged silently.

Full style-guide-level detail (linting config, exact test coverage targets) is a follow-on deliverable **[EXPAND]**.

---

## 16. Design Standards

- **Typography:** Inter (or equivalent) as the primary typeface across the product — consistent with the existing mockups; clear type scale (headline / body / caption / label weights already established in shipped mockups).
- **Color system:** primary indigo/purple accent (`#6C5CE7` family, matching shipped mockups), semantic colors for status (green = on track/excellent, amber = needs review, red = at risk, blue = informational/in progress).
- **Spacing:** consistent 4px-based spacing scale; card padding and gaps standardized (14–16px) across modules.
- **Components:** shared shell (sidebar + main + right intelligence rail), status pills, stat cards, row cards — all reused across modules rather than reinvented per screen (see §6.4).
- **Icons:** simple line icons (stroke-based, 2px weight), consistent sizing (16px in nav, 14–20px elsewhere).
- **Motion:** subtle, purposeful only — state transitions (card status change, approval confirmation), not decorative animation. Consistent with the "calm" philosophy in §2.5.
- **Accessibility:** visible keyboard focus states, sufficient color contrast on status pills (verify amber/red against white background), reduced-motion support.

Full design token specification (exact hex values, complete type scale, component library documentation) is a follow-on deliverable **[EXPAND]** — the shipped mockups are the current source of truth for exact values until this is formalized.

---

## 17. Security & Compliance Standards

### 17.1 RBAC (Role-Based Access Control)

Three roles at MVP: **Owner** (full access, billing, account deletion), **Admin** (team/integration management, all module data), **Member** (scoped to assigned customers/projects/meetings unless org policy grants broader visibility). Finer-grained permissions (per-module, per-record) are a Phase 3+ enterprise feature.

### 17.2 Data Isolation

Per-organization data isolation enforced at the database layer (row-level security or `organization_id` scoping in the ORM layer itself, not just application logic) — this is a hard requirement, not an optimization, since a scoping bug here is a cross-customer data leak.

### 17.3 Integration Security

OAuth scopes least-privilege per integration; connections revocable per-user with a visible "Disconnect" action (already reflected in the Settings mockup's Danger Zone).

### 17.4 Audit & Execution Logs

Every AI Action execution logged: who approved it, what was sent/changed, when. Retained for audit purposes — exact retention period to be set alongside data retention policy (§12.3).

### 17.5 Encryption & Storage

Documents encrypted at rest (Cloudflare R2); access via short-expiry signed URLs, not public links.

### 17.6 Compliance Posture

GDPR-relevant practices (data export, right to deletion) should be designed in from the start even before a formal compliance program; SOC 2 is a Phase 3+/Enterprise-phase undertaking, not an MVP requirement — flagged here so architecture decisions (audit logging, access control) don't have to be retrofitted later.

### 17.7 Sales-Ready Security Posture (before Phase 4, not at Phase 4)

**Gap addressed:** even SMB buyers increasingly ask "how do you secure my Gmail/CRM data" before connecting anything. SOC 2 is correctly deferred to a later phase (§17.6), but that doesn't mean *no* answer exists in the meantime — a design partner asking this question in Phase 1 or Phase 2 needs a plain, honest response, not silence, or the question itself becomes a sales blocker at the exact moment trust matters most.

The baseline answer NeuronOS should be able to state plainly from Phase 1 onward, without overclaiming a certification that doesn't exist yet:

- Documents and sensitive fields are encrypted at rest (§17.5); tokens for connected integrations are encrypted at the application layer with keys held outside the database (Database Spec §8.1).
- OAuth scopes requested are the minimum needed for the feature, and are user-revocable at any time (§17.3).
- Per-organization data isolation is enforced at the database layer, not just in application code (§17.2).
- A plain-language data retention and deletion policy exists and is stated, not just implied: soft-deleted data is recoverable for 30 days, then purged (Database Spec §0.2); a full account deletion is a deliberate, confirmed action (Database Spec §1.1).
- SOC 2 / formal third-party certification is **not yet in place** and it is more honest to say so directly than to imply otherwise — paired with a clear statement of when it's planned (Phase 3+/Enterprise phase, §17.6).

This baseline answer, plus the liability and DPA positions below, are consolidated into a single sales-facing reference document: `NeuronOS_Trust_Security_FAQ.md` — written so it can be shared with a design partner's IT-literate stakeholder directly, not paraphrased ad hoc in every sales conversation.

### 17.8 Liability & ToS Framing for AI-Executed Actions

**Gap addressed:** if an AI Action sends a wrong invoice or a poorly-worded email that damages a customer relationship, there was no stated position on responsibility anywhere in the documentation — and this needs to exist *before* any automation runs unsupervised (§2.3/§2.7), not after an incident.

Position established (full legal-review-ready language is a task for actual counsel — this is the product/engineering-level statement of intent that legal language should be built from, not a substitute for it):

- NeuronOS is explicitly designed so that no financially or relationally significant action executes without an explicit human approval (`severity_tier = 'high'` actions require `confirm_high_severity` — Database Spec §7.1, API Spec §7). The product's Terms of Service should reflect that **the approving human, not NeuronOS, is the party executing the action** for high-severity cases — NeuronOS's role is to draft and recommend, with the human retaining final control and responsibility at the point of send.
- For `live`-mode automations (lower-severity, graduated actions running without per-instance review — §2.3), the ToS should state plainly that the organization's Owner/Admin who advanced or approved the automation into `live` mode accepts responsibility for its ongoing operation, consistent with the fact that graduation itself was a deliberate, logged decision (Database Spec §6.1), not something NeuronOS did unilaterally.
- This position should be reflected in `organizations.terms_accepted_version`/`terms_accepted_at` (Database Spec §1.1) — meaning a specific version of this liability language is what each org's Owner is recorded as having accepted, so the position isn't just written down once and forgotten as the product evolves.

### 17.9 Data Processing Agreement (DPA) Posture

**Gap addressed:** no stated position existed on data processing agreements — not urgent for the earliest design partners, but a real requirement the moment a business with its own compliance obligations wants to connect real data.

- A standard DPA template should exist and be ready to execute on request, even before any customer asks for one — being unable to produce one on short notice reads as unpreparedness at exactly the wrong moment.
- `organizations.dpa_signed_at` (Database Spec §1.1) tracks which orgs have an executed DPA — most won't, and that's expected at this stage; the field exists so the org's compliance posture is queryable rather than tracked in someone's inbox.
- Full DPA terms are a legal-counsel deliverable, not something to draft here — this section establishes that the *product* needs to be ready to support one (data export, deletion, sub-processor disclosure for the LLM providers and cloud infra used) whenever legal produces the actual agreement.

---

## 18. Roadmap

*(Full detail — phase-by-phase scope, exit criteria, and a milestone table — was already produced as a companion document: `NeuronOS_Roadmap_Spec.md`. Summary below; that document is the authoritative detail, and has been updated to reflect the gap-fix pass described in §9.1/§9.2/§2.3 above — most notably: integration provider review now starts as a parallel track from Phase 0/1 rather than sequentially inside Phase 2, and Phase 1's exit criteria now include a validated dry-run/graduated-autonomy path for Automations and a first-pass AI unit-economics check.)*

| Phase | Duration | Outcome |
|---|---|---|
| Phase 0 — Foundations | 4 weeks | Infra, auth, data model, design system ready; provider app registrations/OAuth consent screens for the longest-lead-time integrations (Gmail, Outlook) submitted for review in parallel |
| Phase 1 — MVP Core | 8 weeks | Pulse, Customers, Knowledge, AI Workspace, AI Actions, basic Automations (dry-run/graduating mode only — no `live` automations until real approval history exists) /Reports/Settings usable manually; rough AI unit-economics model validated against a price hypothesis |
| Phase 2 — Connected Intelligence | 10 weeks | Live integrations (Gmail/Drive/Calendar/Outlook, pending provider approval), Projects + Meetings shipped, Context Engine live, automation builder; automations with sufficient approval history begin graduating to `live` |
| Phase 3 — Depth & Autonomy | 12 weeks | More integrations, Learning Engine, AI Action autonomy tiers, mobile, voice |
| Phase 4 — Platform | Ongoing | Plugin/marketplace architecture, Enterprise features, multi-model routing at scale, public API |

Open questions carried over from the roadmap doc (graph DB timing, pricing/plan gating) remain unresolved and should be revisited before Phase 2 commitments are finalized. The integration staleness and Decision Engine confidence-threshold questions have been substantively addressed by the schema/API changes in §9.2 and the Database/API Spec updates — see those documents for the resolution.

---

## 19. Long-Term Vision & Future Modules

- **Marketplace:** third-party and community-built automations/plugins on top of the NeuronOS context layer.
- **Plugins:** a formal SDK for extending NeuronOS with custom integrations or custom AI Actions specific to an industry vertical.
- **AI Employees:** role-specific AI agents (an "AI Sales Manager," an "AI Ops Manager") that operate with a defined scope of autonomy inside a business, building on the AI Actions autonomy-tier work in Phase 3.
- **Voice Command:** already previewed in the mobile mockup ("Ask NeuronOS or give a command...") — full voice interaction as a first-class input method.
- **Enterprise:** SSO, granular permissions, audit exports, data residency options, on-prem/VPC deployment options for customers who need them.

The end-state framing: businesses stop asking "where is the information" and start asking "NeuronOS, what should we do today?" — every module in this document is in service of getting to that single interaction.

---

## 20. Glossary

- **Business Health Score:** a computed single-number summary of overall business state, shown prominently in Pulse.
- **Relationship Score:** per-customer computed score reflecting engagement, risk, and health of that relationship.
- **AI Action:** any AI-suggested action awaiting human review/approval before execution.
- **Context Engine:** the engine responsible for linking entities (customer ↔ email ↔ document ↔ meeting ↔ invoice) into a usable relationship graph.
- **Design partner:** an early customer used to validate the product loop before broader release.
- **Autonomy tier:** the level of independence an AI Action type has been granted (Review-required vs. Auto-with-notify), earned per organization based on approval history.
- **Cold start:** the state of a brand-new organization with no data yet for the AI to reason about — addressed by the onboarding journey in §4.4.
- **Reasoning (field):** the human-readable explanation of the signal behind an AI-generated risk flag or recommendation, shown alongside the conclusion per §2.7 — not an optional detail.
- **Severity tier:** a classification (`low`/`medium`/`high`) on every AI Action reflecting how reversible and financially/relationally significant it is, gating how much confirmation friction it requires (§3.4/Database Spec §7.1).

---

## Document Maintenance

This file should be updated whenever a product, architecture, or design decision changes — not left to drift from reality. Recommended process: any PR that changes product behavior in a way that contradicts this document must update this document in the same PR, or the PR should be blocked in review. Sections marked **[EXPAND]** are the recommended next writing sessions, roughly in this priority order for unblocking engineering work: (1) full API reference remaining gaps (webhook catalog), (2) remaining per-screen UI specs (mobile/tablet mockups for Project/Meeting detail — flagged pending in the screen spec doc), (3) prompt library, (4) coding standards detail, (5) design token spec.

**Changelog:**
- v1.0 → v1.1: resolved the Automations/approve-first philosophy contradiction (§2.3), added integration provider review lead times as an explicit architectural constraint (§9.1), added initial SLO targets (§9.2), added score/algorithm versioning (§12.5), added AI unit-economics tracking to Success Metrics (§1.9) with a companion working spreadsheet (`NeuronOS_Unit_Economics_Model.xlsx`). Corresponding changes applied to `NeuronOS_Database_Spec.md`, `NeuronOS_API_Spec.md`, and `NeuronOS_Roadmap_Spec.md` — see those files' own changelog/open-items sections for exact diffs.
- v1.1 → v1.2 (this pass): added the cold-start onboarding journey as new §4.4, with a companion `NeuronOS_Onboarding_Spec.md`; added the "show reasoning, not just conclusions" principle as new §2.7, backed by `reasoning`/`confidence_score` fields on `ai_actions` and `risk_flags`; added the Context Engine correction loop (§14.1) for AI-inferred entity links; added severity-tier gating on AI Actions (§5.9) so irreversible/high-stakes actions get visibly higher-friction confirmation; substantially expanded Chapter 17 with a sales-ready security posture (§17.7), liability/ToS framing for AI-executed actions (§17.8), and a DPA posture (§17.9), consolidated into a new companion document `NeuronOS_Trust_Security_FAQ.md`. Corresponding schema/API changes are in the updated `NeuronOS_Database_Spec.md` and `NeuronOS_API_Spec.md`.
