# NeuronOS

**The Intelligence Layer for Every Business.**

NeuronOS is an AI-native business intelligence platform that connects to a company's existing tools (Gmail, CRM, calendars, accounting) and turns scattered data into prioritized, actionable recommendations — without requiring anyone to migrate off what they already use.

## Status

**Phase 0 — Foundations, in progress.** See `docs/NeuronOS_Roadmap_Spec.md` for exit criteria. Built so far:

- Auth: org/owner signup, login, invite + accept-invite, terms acceptance, JWT refresh
- Full database schema (all MVP + Phase 2 tables) via Alembic, with Postgres RLS enforced by a restricted `neuronos_app` role — see `NeuronOS_Database_Spec.md` §0.1
- Frontend shell: signup/login pages, Pulse's cold-start onboarding-selector state, design tokens matching the mockups
- CI: backend (pytest against a real Postgres service container) and frontend (typecheck + lint + build)

**Not yet done (tracked in the Roadmap, not silently skipped):**
- Google/Microsoft OAuth provider-review submissions (Roadmap §2A) — this needs a human with the actual business/Google Cloud/Azure accounts; it cannot be done by an AI agent. See "Provider Review Track" below.
- Everything scoped to Phase 1+ (Customers, Knowledge, AI Actions, Automations, Reports, Settings) — the schema exists for these already; no application code does yet, by design (`NeuronOS_Database_Spec.md` §9).

## Start Here

**If you are an AI coding agent (Claude Code, Cursor, etc.) or a new engineer on this project, do not write any code before reading `docs/NeuronOS_Master_Build_Prompt.md` in full.** It is the required first read for this repo — see `CLAUDE.md` for the short version of why.

## Running Locally

### Backend

Requires a local Postgres (with the `pgvector` extension — use the `pgvector/pgvector:pg16` Docker image, not plain `postgres`).

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate  # or .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"

# Run a disposable Postgres:
docker run -d --name neuronos-pg -e POSTGRES_USER=neuronos -e POSTGRES_PASSWORD=neuronos \
  -e POSTGRES_DB=neuronos -p 5432:5432 pgvector/pgvector:pg16

export MIGRATIONS_DATABASE_URL="postgresql+asyncpg://neuronos:neuronos@localhost:5432/neuronos"
export DATABASE_URL="postgresql+asyncpg://neuronos_app:neuronos_app_dev_only@localhost:5432/neuronos"
alembic upgrade head   # creates the schema AND the restricted neuronos_app role — see Database Spec §0.1.1

export JWT_SECRET="dev-secret"
uvicorn app.main:app --reload --port 8000
```

**Any real (non-local) environment:** set `NEURONOS_APP_ROLE_PASSWORD` from that environment's own secrets mechanism *before* running `alembic upgrade head` there for the first time — the migration reads it only at the moment it creates the `neuronos_app` role (Database Spec §0.1.1), so there's no separate manual rotation step to remember. It is **not** re-read on later migration runs; rotating an already-created role's password is a deliberate `ALTER ROLE` action, done outside the migration.

Run tests (spins its own migration up/down against `MIGRATIONS_DATABASE_URL`'s target — point this at a scratch database, not one with real data):

```bash
pytest -v
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL — defaults to http://localhost:8000/api/v1
npm install
npm run dev
```

## Provider Review Track (Roadmap §2A) — requires a human, not an agent

Per `MASTER_BLUEPRINT.md` §9.1 and `NeuronOS_Roadmap_Spec.md` §2A, Gmail/Google Drive/Outlook OAuth review has the longest lead time in the whole integration list and is meant to start in Phase 0, in parallel with engineering — **this is the one Phase 0 work item an AI agent cannot execute**, since it requires:
1. A real Google Cloud project and a real Microsoft Azure AD app registration, tied to an actual business/domain identity.
2. Submitting Google's OAuth consent screen for verification (and CASA assessment if requesting broad Gmail scopes — consider `gmail.readonly` first, Database Spec §8.1's scope-minimization note).
3. Submitting Microsoft's publisher verification.
4. An assigned human owner for this track end-to-end (Roadmap §2A) — recurring external correspondence, not a one-time task.

Whoever picks this up next should start it now, regardless of which other Phase 0/1 work is in progress — it's the most likely thing to gate the Phase 2 timeline.

## Documentation

All product, architecture, and design documentation lives in `docs/`:

| File | What it covers |
|---|---|
| `MASTER_BLUEPRINT.md` | Vision, philosophy, architecture, standards — the source of truth everything else derives from |
| `NeuronOS_Roadmap_Spec.md` | Phased build plan, exit criteria, integration-review timeline |
| `NeuronOS_Database_Spec.md` | Full schema |
| `NeuronOS_API_Spec.md` | Full API reference |
| `NeuronOS_Onboarding_Spec.md` | Cold-start first-run flow |
| `NeuronOS_Trust_Security_FAQ.md` | Security, liability, and DPA posture |
| `NeuronOS_Screen_Specs_Project_Meeting_Detail.md` | Per-screen UI spec standard |
| `NeuronOS_Strategic_Gap_Analysis.md` | Known risks and gaps, with resolutions tracked |
| `NeuronOS_Unit_Economics_Model.xlsx` | AI cost-per-organization model |
| `NeuronOS_Master_Build_Prompt.md` | The system prompt to load every session — start here |
| `mockups/` | Visual/interaction source of truth — interactive HTML (AI Actions/Automations detail, Projects/Meetings) plus `UI_design1.png`/`UI_design2.png` (full-product statics: Pulse, Customers, Knowledge, Reports, Settings, mobile + dark-mode previews) |

## Structure

```
neuronos/
├── docs/           # Read this first — see above
├── frontend/       # Next.js 15 / React 19 / TypeScript
├── backend/        # FastAPI / Python 3.12
└── .github/        # CI/CD
```

## Tech Stack

Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, React Hook Form, Zod.
Backend: FastAPI, Python 3.12, SQLAlchemy, Alembic, Celery, Redis.
Database: PostgreSQL + pgvector, Redis, Cloudflare R2.
AI: LangGraph, multi-model routing (Claude / OpenAI / Gemini).

Full rationale for each choice is in `MASTER_BLUEPRINT.md` §8.
