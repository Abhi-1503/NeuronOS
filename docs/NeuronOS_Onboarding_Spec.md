# NeuronOS Onboarding Specification (Cold-Start Flow)

**Derives from:** MASTER_BLUEPRINT.md §4.4, Strategic Gap Analysis §3.1, NeuronOS_Database_Spec.md §1.3, NeuronOS_API_Spec.md §5B
**Status:** Implementation-ready v1
**Purpose:** Solve the single biggest activation risk identified in the Strategic Gap Analysis — a brand-new organization has zero data, so Pulse, the AI Workspace, and Customer risk scoring have nothing to reason about. This document specifies exactly what a new user sees between signup and their first real, trustworthy insight.

---

## 1. The Problem This Solves

Every other module spec in this project assumes data already exists — a Customer to score, a Document to summarize, a Meeting to brief. None of that is true for organization #1, minute #1. Without a deliberate design for this moment, Pulse's Business Health score is either blank or meaningless, the AI Workspace has nothing to answer questions about, and the product's entire value proposition — "trust what it tells you" — has no evidence behind it yet. This is the moment a new user decides whether NeuronOS is real or a shell.

**Design principle:** get to one genuinely correct, specific insight within minutes — not after a "full sync," and not by forcing every module to be populated first.

---

## 2. The Three Entry Paths

A new organization's Owner picks exactly one path to start (can add the others later — this is not an exclusive choice, just a starting point):

| Path | What the user does | Time to first insight | Best for |
|---|---|---|---|
| **A. Connect an integration** | Connect Gmail (or another supported provider) | Minutes — NeuronOS syncs *recent* email only (e.g., last 30 days), not full mailbox history, specifically to keep this fast | Users who live in their inbox and want NeuronOS to work with what's already there |
| **B. Upload key documents** | Upload 3–5 documents (a customer list, a contract, a proposal) | Minutes — one document is enough to generate a real AI summary and, if it names a customer, seed a Customer record | Users who have a handful of documents that capture most of what matters |
| **C. Add top customers manually** | Add name + last contact date for their 5 most important customers | Under a minute — no processing wait at all | Users who want the fastest possible path and are comfortable with manual entry |

All three paths are equally valid and equally supported — there is no "real" path and a fallback. The product should not imply Path C is a lesser experience; for many small service businesses, five customers typed in by hand is a completely honest starting point.

---

## 3. Flow Specification

### 3.1 Step-by-step

```
1. Sign up, create organization
     ↓
2. "How do you want to get started?" — path selector (Path A / B / C above)
   This screen IS Pulse's first-run state — not a separate wizard the user
   clicks through before "the real product" appears.
     ↓
3. Path-specific quick action:
   A: OAuth consent → background sync of recent data only
   B: Drag-and-drop upload of up to 5 files
   C: A simple repeating form: customer name + last contact date (x5)
     ↓
4. Within minutes: NeuronOS generates ONE real, specific AI Action from
   whatever was just provided — not a demo, not a placeholder
     ↓
5. This AI Action appears in the AI Actions queue exactly like any other —
   approving or dismissing it is the user's first real interaction with
   the "review reasoning, then decide" trust loop (Blueprint §2.7)
     ↓
6. organizations.onboarding_first_insight_at is set the moment this first
   AI Action is generated (Database Spec §1.3) — this is the activation
   metric, not step 2 or step 3
     ↓
7. Prompted (not forced) to add another data source — "Want to also
   connect your calendar?" as a dismissible suggestion, not a gate
```

### 3.2 What "one real, specific insight" means per path

This is the part that must not be generic — a placeholder-feeling first insight defeats the entire purpose of this flow.

- **Path A (Gmail connected):** scan the synced recent emails for the most overdue-looking thread (e.g., a sent email with no reply after N days from a sender not yet in the Customers list) → AI Action: "I noticed no reply from [contact] in 6 days on the '[subject]' thread. Want me to draft a follow-up?"
- **Path B (documents uploaded):** if a document names a customer or contains a date (e.g., a contract with an expiry date, a proposal with a value), surface that directly → AI Action: "This contract with [customer] renews in 45 days. Want me to add a reminder?"
- **Path C (customers added manually):** compare each `last_contact_at` against today → AI Action: "You added [customer] — I don't see contact in the last 12 days. Want me to draft a check-in?"

In all three cases, the AI Action must show its `reasoning` field per Blueprint §2.7 — even (especially) on this first interaction, since it's the moment that sets the user's trust calibration for everything after it.

### 3.3 What happens if there's genuinely nothing to flag

Sometimes the honest answer is "everything looks fine so far" (e.g., Path C with 5 customers all contacted yesterday). This should **not** be forced into a fabricated risk just to have something to show. Instead:

- Show a confirming, still-specific message: "All 5 customers you added were contacted within the last week — nothing needs attention right now. As you add more data, I'll start catching things you'd otherwise miss."
- This still counts as reaching the "first insight" milestone (`onboarding_first_insight_at` is set) — a correct "nothing's wrong" is a real insight, not a failure to produce one. Fabricating a risk to avoid an empty-feeling moment would be a worse trust violation than showing an honest all-clear.

---

## 4. UI Notes

- The path selector (step 2) reuses Pulse's existing visual shell (Blueprint §6.4) rather than introducing a separate onboarding-specific layout — this is deliberately the first thing shown *inside* Pulse, not a modal or a separate route that feels disconnected from the product proper.
- Each path's quick action (step 3) should be completable without leaving the current screen — no multi-page wizard.
- The "prompted, not forced" follow-up (step 7) should be dismissible permanently per suggestion (don't re-nag with the same suggestion every session) but should reappear in a different form if the user's data genuinely stays thin after a week (e.g., a gentler Pulse card: "Your insights get sharper with a bit more data — want to add more customers?").

---

## 5. API Support

See `NeuronOS_API_Spec.md` §5B: `GET /onboarding/status`, `POST /onboarding/select-method`, `POST /onboarding/complete`. Database support in `NeuronOS_Database_Spec.md` §1.3.

---

## 6. Success Metric

`organizations.onboarding_first_insight_at` (time from `created_at` to this timestamp) is the "time-to-insight" metric named in Blueprint §1.9 — this document exists specifically to make that number small and honest, not just fast. A fast but fabricated or generic first insight would defeat the purpose; the target is fast **and** genuinely correct.

## 7. Open Items

1. Exact thresholds used to detect "nothing to flag" per path (§3.3) need tuning against real early-user data — the illustrative day-counts above (6 days, 12 days) are starting points, not validated numbers.
2. Whether Path A's "recent data only" sync window (30 days suggested) is the right default, or whether it should be configurable per provider, is worth revisiting once real sync-time data exists from Phase 2 integration work.
3. This spec assumes a single-person setup flow (the Owner does onboarding alone). A multi-person kickoff (e.g., an agency onboarding with 3 team members at once) may need a different flow — not addressed here, flagged for whoever picks this up next.
