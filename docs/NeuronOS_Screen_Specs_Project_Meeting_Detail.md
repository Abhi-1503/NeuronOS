# NeuronOS Screen Specifications — Project Detail & Meeting Detail

**Derives from:** MASTER_BLUEPRINT.md §6.3 (Per-Screen Documentation Standard), NeuronOS_Database_Spec.md, NeuronOS_API_Spec.md
**Status:** Implementation-ready v1
**Companion file:** `neuronos_project_meeting_detail.html` (visual mockup, matching the shipped shell)

These are the two detail views flagged as open work in the Roadmap doc (§18) and the Master Blueprint (§6.2) — the list views for Projects and Meetings were already specified and mocked; this document specifies where a user lands after clicking into a specific project or meeting.

---

## 1. Project Detail

### 1.1 Purpose

Give the person responsible for a project (or checking on one) a single place to see its full state — progress, risk, tasks, dependencies, history, and files — plus an AI-generated read on what's likely to go wrong before it does.

### 1.2 User Goal

"Is this project okay, and if not, what exactly is wrong and what should I do about it?" — not just "what's the status," but "what's the next concrete action."

### 1.3 Components

- **Header band:** project name, linked customer (if any) as a clickable chip, status pill, deadline, progress bar with percentage, primary action button (`Edit` / `Mark Complete` depending on status).
- **Tab bar:** Overview · Tasks · Timeline · Dependencies · Files · Notes.
- **Overview tab:** description, key dates, team member avatars with roles (lead/contributor/reviewer), open risk flag count with severity breakdown.
- **Tasks tab:** grouped by status (To Do / In Progress / Blocked / Done) in a kanban-style column layout on desktop, flat filterable list on mobile; each task shows title, assignee avatar, due date, and a small badge if `source = meeting_action_item` (with a link back to the originating meeting).
- **Timeline tab:** chronological log of everything that's happened on the project (status changes, task completions, risk flags raised/resolved, files added) — read-only, system-generated.
- **Dependencies tab:** list/graph of what this project is blocked by or blocking (other projects, or external factors like "waiting on client data") — MVP renders as a simple list; a visual dependency graph is a Phase 2+ enhancement, not required for first ship.
- **Files tab:** documents linked to this project (via `linked_entities`), reusing the Documents module's file card component.
- **Notes tab:** freeform internal notes, threaded by author and timestamp.
- **Right intelligence rail (persistent across all tabs):** AI Summary card, Risks & Blockers list (reused from the list-view right rail, filtered to this project — each flag shows its `reasoning` per Blueprint §2.7, not just the conclusion), Recommended Action card with one-click draft/execute — same pattern as the Projects list view, per Blueprint §6.4.

### 1.4 Layout

- **Desktop (≥1280px):** shell unchanged (220px sidebar / main / 300px right rail). Main content: header band full-width, tab bar below it, tab content below that. Tasks tab uses a 4-column kanban.
- **Tablet (768–1279px):** right rail collapses to a toggleable drawer (icon in the header band opens it as an overlay) so the main content gets full width. Tasks tab kanban drops to 2 columns, horizontally scrollable.
- **Mobile (<768px):** sidebar becomes a bottom nav or hamburger drawer (consistent with whatever pattern the existing mobile mockup already established for Pulse). Tab bar becomes horizontally scrollable pills. Tasks tab is a flat list grouped with section headers instead of kanban columns. Right rail content appears as a separate "Insights" tab rather than a persistent rail.

### 1.5 States

- **Loading:** skeleton header band (gray blocks for name/status/progress) + skeleton tab content; right rail shows a skeleton AI Summary card. Do not block the whole page on the AI Summary being ready — it can load in after the rest of the page.
- **Error:** if the project fails to load (404 or permission denied), show a full-page state: "This project isn't available" with a link back to the Projects list — never show a half-populated page with silently missing data.
- **Empty (Tasks tab, no tasks yet):** "No tasks yet. Break this project into steps to track progress." with a prominent "Add Task" button — an invitation to act, not a dead end.
- **Empty (Dependencies tab, none set):** "Nothing is currently blocking this project." — stated plainly, not as a decorative illustration.

### 1.6 Animations & Transitions

- Tab switches: content cross-fades (150ms), no sliding — consistent with the "calm" motion philosophy (Blueprint §16).
- Progress bar updates (e.g., after a task is marked done and progress recalculates): animate the fill over ~400ms rather than jumping instantly, so the change is perceivable.
- Kanban card drag between status columns (Tasks tab): standard drag-and-drop with a subtle lift shadow on pick-up; on drop, the card settles with no bounce/overshoot.
- Risk flag resolution: the resolved flag fades out of the Risks & Blockers list rather than disappearing instantly.

### 1.7 AI Interaction Points

- **AI Summary card:** generated by the Action Engine, refreshed whenever the project's underlying data changes materially (new risk flag, status change, deadline passed) — not on every page load, to control cost.
- **Recommended Action card:** sourced from the AI Actions queue filtered to this project's `related_entity_id` — clicking the action button here is the same `POST /ai-actions/{id}/approve` flow as the AI Actions screen, just surfaced contextually. **The card must show the action's `reasoning` and, if present, `confidence_score` inline** (Blueprint §2.7, Database Spec §7.1) — not just the drafted content — and if `severity_tier = 'high'`, the button here triggers the same secondary confirmation step required everywhere else in the product (§2.7/Database Spec §7.1), not a shortcut around it just because it's surfaced contextually.
- **Risk flags:** generated by the Decision Engine (see Database Spec §3.4) — displayed, not editable directly by the user; a user can only "Resolve" a flag (marks it addressed), not edit its description, to keep the audit trail honest.

### 1.8 Accessibility

- Tab bar is keyboard-navigable (arrow keys move between tabs, matching standard ARIA tabs pattern); each tab panel has `role="tabpanel"` and `aria-labelledby` referencing its tab.
- Kanban drag-and-drop must have a keyboard-accessible alternative (e.g., a "Move to..." menu on each card) — drag-only interaction is not acceptable.
- Status pills carry a text label, not color alone (already true in shipped mockups — carry this forward here).
- Progress bar has an `aria-valuenow`/`aria-valuemax` pair for screen readers, not just a visual fill.

### 1.9 Business Logic Triggered by This Screen

- Loading the screen does **not** trigger a recompute of the AI Summary or risk flags — those are computed asynchronously by the Decision/Action Engines on a schedule or on relevant data changes, and this screen only reads the latest cached result. This keeps page load fast and predictable in cost.
- Marking a task "Done" that was the last incomplete task auto-recalculates `progress_pct` and may trigger a status change suggestion (e.g., "Mark project Complete?") surfaced as a toast, not an automatic status change — a human always confirms the project-level status transition.
- Resolving the last unresolved risk flag on an `at_risk` project does not automatically flip its status back to `on_track` — that's a judgment call left to the project lead, consistent with the "approve-first" philosophy (Blueprint §2.3).

### 1.10 API Calls

| Trigger | Call |
|---|---|
| Page load | `GET /projects/{id}` |
| Load Tasks tab | `GET /projects/{id}/tasks` |
| Load Files tab | via linked documents (`GET /documents/search` scoped to this project's `linked_entities`, or a dedicated `GET /projects/{id}/documents` if added — flagged as a small API gap: not explicitly listed in the API Spec, should be added) |
| Add task | `POST /projects/{id}/tasks` |
| Update task status (drag) | `PATCH /projects/{id}/tasks/{task_id}` |
| Resolve risk flag | `POST /projects/{id}/risk-flags/{flag_id}/resolve` |
| Approve recommended action | `POST /ai-actions/{id}/approve` |
| Edit project details | `PATCH /projects/{id}` |

### 1.11 Permissions

- **View:** any `project_member`, plus Admin/Owner org-wide (per API Spec §3, `GET /projects/{id}`).
- **Edit project fields, mark complete:** project lead, Admin, Owner (`PATCH /projects/{id}`).
- **Add/edit tasks:** any project member.
- **Resolve risk flags:** project lead, Admin, Owner.
- **Add member:** project lead, Admin, Owner.
- A Member who is not a project member attempting to navigate directly to this screen (e.g., via a stale link) sees the Error state (§1.5), not a permission-denied screen with details about the project — the error message should not leak project existence/metadata to someone without access.

### 1.12 Acceptance Criteria

- [ ] Screen loads and renders header band within 500ms of navigation on a warm cache (excluding AI Summary, which may load in after).
- [ ] All four project statuses (`on_track`, `at_risk`, `needs_review`, `in_review`) render with distinct, correctly-labeled status pills matching the design system.
- [ ] Tasks tab correctly reflects real-time task counts matching what's shown in the Overview tab (no drift between tabs).
- [ ] A task created from a promoted meeting action item (§4 below) shows its originating-meeting badge and the badge links correctly to that meeting's detail screen.
- [ ] Resolving a risk flag updates both this screen and the Projects list view's risk count without requiring a manual refresh (via query cache invalidation).
- [ ] All interactive elements are reachable and operable via keyboard alone.

### 1.13 Edge Cases

- Project with no linked customer (internal project): customer chip in header band is omitted entirely, not shown empty.
- Project with zero team members (shouldn't normally happen, but a member could be removed from the org): Overview tab shows "No team members assigned" rather than an empty avatar row.
- Deadline in the past but status still `on_track`: this is a real, valid state (project finished early or deadline was met) — the UI must not auto-flag this as at-risk; only the Decision Engine's actual risk-flag logic determines risk, not a naive "deadline < today" check in the UI layer.
- Extremely long project names: truncate with ellipsis in the header band, full name available on hover/focus (tooltip) and always shown in full on the Projects list view's detail link target (i.e., don't truncate the only place the full name exists).
- Concurrent edits (two users editing the same project's status simultaneously): last-write-wins at the API layer; the losing client should get a `409 conflict` from `PATCH /projects/{id}` (per API Spec pattern) and should refetch and show the other user's change rather than silently retrying with stale data.

---

## 2. Meeting Detail

### 2.1 Purpose

Give a user everything about one meeting — before it happens (the brief), during/after it (notes or transcript), and what came out of it (summary and action items) — in one place, so nothing discussed gets lost.

### 2.2 User Goal

Before the meeting: "What do I need to know to walk in prepared?" After the meeting: "What did we agree to, and did it get turned into real follow-up?"

### 2.3 Components

- **Header band:** meeting title, linked customer (if any) as a clickable chip, scheduled date/time, platform icon + duration, status pill (Upcoming / Brief Ready / Completed / Needs Notes), primary action button (`Join` if upcoming and within a join window, `Generate Summary` if completed but unsummarized).
- **Tab bar:** Brief · Notes/Transcript · Action Items · Attendees.
- **Brief tab:** AI-generated pre-meeting brief — summary paragraph, talking points list, related context cards (open proposal, outstanding invoice, recent related documents) — this is the same content shown in the right rail preview on the Meetings list view, expanded to full detail here.
- **Notes/Transcript tab:** for upcoming meetings, an editable agenda/notes field; for completed meetings, either the raw transcript (if captured via integration) or manually entered notes, plus the AI-generated summary rendered above the raw content.
- **Action Items tab:** checklist of extracted action items, each with a "Promote to Task" button (if not already promoted) showing which project it was sent to once promoted.
- **Attendees tab:** list of attendees (internal users and external customer contacts), each row showing name, role/title if known, and — for customer contacts — a link to their customer record if `customer_id` is set on the meeting.
- **Right intelligence rail:** for upcoming meetings, mirrors the Brief tab's talking points as a persistent quick-reference; for completed meetings, shows the Action Items checklist (reused from the list-view right rail pattern) plus a "Related Meetings" list (other meetings with the same customer).

### 2.4 Layout

Same responsive pattern as Project Detail (§1.4): desktop keeps the persistent right rail, tablet collapses it to a drawer, mobile moves rail content into its own tab and turns the tab bar into scrollable pills.

### 2.5 States

- **Loading:** skeleton header band; Brief tab shows a skeleton summary paragraph and 3 skeleton talking-point lines while the AI brief is being generated or fetched.
- **Brief not yet generated (upcoming meeting, outside the generation window — see §2.9):** Brief tab shows "Your brief will be ready 24 hours before this meeting" rather than a generic empty state — the reason for the empty state is itself useful information.
- **Error (summarization failed):** Notes/Transcript tab shows "We couldn't generate a summary from these notes" with a "Try Again" button and an option to write a manual summary instead — never a dead end.
- **Empty (Action Items tab, none extracted):** "No action items were identified from this meeting." — plain statement, with a manual "Add Action Item" option, since extraction can legitimately miss things.

### 2.6 Animations & Transitions

- Same tab cross-fade pattern as Project Detail (§1.6).
- Action item checkbox: standard check animation on completion; promoting an item to a Task animates the button into a small "View Task →" link rather than disappearing, so the user retains a path to what they just created.
- Brief generation (if triggered synchronously per API Spec §4's `GET /meetings/{id}/brief` behavior): show a lightweight inline loading state ("Preparing your brief...") within the Brief tab rather than blocking the whole screen.

### 2.7 AI Interaction Points

- **Brief generation:** Action Engine, using Context Engine data about the linked customer/project plus recent related documents — this is the single most AI-dependent moment in the whole product's daily use, per the User Journey in Blueprint §4.
- **Summarization:** Action Engine, triggered explicitly by the user via `POST /meetings/{id}/summarize`, not automatically on meeting end (the meeting platform integration signaling "meeting ended" is a Phase 2+ trigger — MVP requires the user to initiate summarization once notes/transcript are available).
- **Action item extraction:** happens as part of the summarization job, not a separate call.

### 2.8 Accessibility

- Same tab ARIA pattern as Project Detail (§1.8).
- Action item checkboxes are real checkable elements (native `<input type="checkbox">` or an ARIA `role="checkbox"` with proper state), not divs styled to look checked.
- Attendee list rows with external links (to a customer record) are clearly distinguishable from internal-only rows for screen reader users (e.g., "View customer record for Jane Doe" as the accessible name, not just "View").

### 2.9 Business Logic Triggered by This Screen

- The pre-meeting brief generation window (default: within 24 hours of `scheduled_at`) is a configurable org-level setting, not hardcoded — some businesses may want briefs generated further ahead for meetings that need more prep.
- Promoting an action item to a Task (`POST /meetings/{id}/action-items/{item_id}/promote`) requires the user to pick a target project — if the meeting is linked to a customer with exactly one open project, pre-select it as a default but still require explicit confirmation, never auto-promote silently.
- A meeting's status auto-transitions from `upcoming` → `needs_notes` a set time after `scheduled_at` + `duration_minutes` has passed with no summary generated yet (background job) — this is what drives the "Needs Notes" tab on the list view; the transition to `completed` happens only once a summary exists, not just because time has passed.

### 2.10 API Calls

| Trigger | Call |
|---|---|
| Page load | `GET /meetings/{id}` |
| Load Brief tab | `GET /meetings/{id}/brief` |
| Load Action Items tab | `GET /meetings/{id}/action-items` |
| Submit notes/transcript for summarization | `POST /meetings/{id}/summarize` |
| Promote action item | `POST /meetings/{id}/action-items/{item_id}/promote` |
| Join meeting | opens `platform` link stored on the meeting (no API call — this is a client-side redirect using stored meeting link metadata; note the current schema doesn't have an explicit `join_url` column — flagged as a database gap, see §3 below) |

### 2.11 Permissions

- **View:** any attendee (`meeting_attendees` where `user_id` = requester), Admin, Owner.
- **Submit summary / promote action items:** any attendee, Admin, Owner.
- **Edit meeting details (reschedule, etc.):** meeting creator, Admin, Owner — not every attendee, since attendees may include people without edit rights on the meeting itself.
- Same non-leaking error behavior as Project Detail (§1.11) for unauthorized direct navigation.

### 2.12 Acceptance Criteria

- [ ] Brief tab correctly shows the "not yet ready" state vs. loading state vs. populated state as distinct, correctly-triggered conditions (not just one generic empty state covering all three).
- [ ] Promoting an action item updates the Action Items tab, the Meetings list view's "Action Items Created" stat, and the target project's Tasks tab, all without requiring a manual page refresh.
- [ ] A meeting's status pill accurately reflects its lifecycle stage and matches what's shown for the same meeting on the Meetings list view (no drift between list and detail).
- [ ] Attendee rows correctly distinguish internal users from external customer contacts, both visually and for assistive technology.
- [ ] All interactive elements are reachable and operable via keyboard alone.

### 2.13 Edge Cases

- Meeting with no linked customer (internal meeting, e.g., sprint review): customer chip omitted, "Related Meetings" in the right rail is omitted or replaced with "Related Projects" if a project link exists instead.
- Meeting rescheduled after a brief was already generated: the existing brief becomes stale — the screen should show a "This brief may be out of date — meeting was rescheduled" notice rather than silently presenting stale talking points as current.
- Very short meetings (e.g., 15-minute calls) with no transcript and no notes ever entered: status remains `needs_notes` indefinitely — the UI should surface these clearly on the list view (already handled by the `needs_notes` tab) rather than have them silently age out of visibility.
- Duplicate/overlapping meetings with the same customer on the same day: no special handling required at this screen level — each meeting is an independent record; any "you have two meetings with ABC Ltd today" observation is a Pulse-level insight, not something this screen needs to detect itself.

---

## 3. Gaps Identified While Writing This Spec

Writing these two screens surfaced two small gaps against the existing Database/API specs — flagging rather than silently patching them into this document:

1. **No `join_url` / meeting link column** on `meetings` (Database Spec §4.1) — needed for the "Join" button's redirect target. Recommend adding `join_url TEXT` to the `meetings` table in the next migration pass.
2. **No dedicated "documents for a project" endpoint** — Files tab (§1.10) currently has to fall back to a generic document search scoped by `linked_entities`, which works but is awkward. Recommend adding `GET /projects/{id}/documents` (and the equivalent `GET /meetings/{id}/documents`) as thin wrappers over the `linked_entities` join, for a cleaner frontend integration.

Neither gap blocks building these screens — both endpoints/columns can be added in a small follow-up migration/PR before or during frontend implementation.

### 3.1 Gaps Since Resolved Elsewhere (cross-referenced, not re-litigated here)

- **Mobile/tablet mockups for both detail screens** were flagged as missing in the Strategic Gap Analysis (§4.7) — this is now an explicit required deliverable in Phase 2 of `NeuronOS_Roadmap_Spec.md`, rather than an indefinitely deferred item. The responsive behavior described in §1.4/§2.4 above is the prose spec these mockups should be built against.
- **Idempotency on side-effecting actions triggered from these screens** — specifically "Promote to Task" (§2.10) and "Approve" on a recommended action (§1.10) — is now a hard requirement per Database Spec §7.4 and API Spec §0.5 (`Idempotency-Key` header). No change needed to this document's API call tables since the header is a cross-cutting requirement documented once at the API Spec level, not repeated per endpoint here — but frontend implementation of these two buttons specifically should generate and reuse an idempotency key per click, consistent with that requirement.
- **Reasoning/confidence display and severity-gated confirmation** (Strategic Gap Analysis §3.2/§3.4) are now reflected directly in this document's Recommended Action card and Risks & Blockers list descriptions (§1.3/§1.7) rather than only cross-referenced — since these two screens are exactly where a business owner encounters an AI-generated risk claim in context, getting this right here matters as much as on the AI Actions screen itself.
