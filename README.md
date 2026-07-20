# NeuronOS

**The Intelligence Layer for Every Business.**

NeuronOS is an AI-native business intelligence platform that connects to a company's existing tools (Gmail, CRM, calendars, accounting) and turns scattered data into prioritized, actionable recommendations — without requiring anyone to migrate off what they already use.

## Status

Pre-MVP. See `docs/NeuronOS_Roadmap_Spec.md` for the current phase and exit criteria.

## Start Here

**If you are an AI coding agent (Claude Code, Cursor, etc.) or a new engineer on this project, do not write any code before reading `docs/NeuronOS_Master_Build_Prompt.md` in full.** It is the required first read for this repo — see `CLAUDE.md` for the short version of why.

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
| `mockups/` | Reference HTML mockups — visual/interaction source of truth |

## Structure

```
neuronos/
├── docs/           # Read this first — see above
├── frontend/       # Next.js 15 / React 19 / TypeScript (not yet scaffolded)
├── backend/        # FastAPI / Python 3.12 (not yet scaffolded)
└── .github/        # CI/CD
```

## Tech Stack

Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query.
Backend: FastAPI, Python 3.12, SQLAlchemy, Alembic, Celery, Redis.
Database: PostgreSQL + pgvector, Redis, Cloudflare R2.
AI: LangGraph, multi-model routing (Claude / OpenAI / Gemini).

Full rationale for each choice is in `MASTER_BLUEPRINT.md` §8.
