# CLAUDE.md

**Before doing anything else in this repo — reading code, writing code, answering a question about the project — read `docs/NeuronOS_Master_Build_Prompt.md` in full and follow it.**

That file is the actual system prompt for this project. It tells you:
- which documents in `docs/` to read and in what order
- the non-negotiable product/architecture principles (approve-first AI actions, visible reasoning/confidence, severity-gated confirmation, idempotency, cold-start onboarding)
- the exact tech stack to use
- how to work session-to-session (state the current Roadmap phase, confirm scope before building, flag contradictions instead of guessing)
- the definition of done for any feature
- the first task to execute, which ends with **waiting for confirmation before writing application code**

Do not skip this. Do not proceed from assumptions about what these documents probably say. This file exists specifically so every session — yours or a future one — starts from the same understanding instead of re-deriving it from scratch.
