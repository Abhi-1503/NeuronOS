# NeuronOS Trust & Security FAQ

**Derives from:** MASTER_BLUEPRINT.md §17.7–17.9, Strategic Gap Analysis §5
**Status:** v1 — written to be shared directly with a design partner's technical/compliance stakeholder
**Purpose:** Answer the questions a real business will ask before connecting their Gmail, CRM, or financial data to NeuronOS — honestly, without overclaiming certifications that don't exist yet, and without staying silent on the parts that aren't fully built out yet either.

> **Note on how to use this document:** this is written to be handed to a design partner as-is, or lightly adapted. It is intentionally honest about what is *not* yet true (no SOC 2 yet, no DPA program yet) rather than vague — vagueness reads as evasive to a technical evaluator, and a plain "not yet, here's when" is more trustworthy than implying more maturity than exists. This document should be reviewed by actual legal counsel before being treated as binding language in a contract — it is the product/engineering-level statement of intent that legal language should be built from, not a substitute for legal review.

---

## 1. "How do you secure my data?"

**Encryption:**
- Documents are encrypted at rest (Cloudflare R2).
- OAuth tokens for connected integrations (Gmail, CRM, etc.) are encrypted at the application layer before storage — never stored in plaintext — with encryption keys held outside the database in a dedicated secrets manager, not alongside the encrypted data itself.
- Document access uses short-expiry signed URLs, not permanent public links.

**Access control:**
- Every organization's data is isolated at the database layer itself (row-level security), not just by application code — meaning a bug in application logic cannot leak one customer's data to another, because the database itself refuses cross-organization queries.
- Role-based permissions (Owner / Admin / Member) control who inside your organization can see or act on what.

**OAuth scope minimization:**
- We request the minimum scope needed for each integration's actual functionality — for example, preferring read-only or metadata-level access over full mailbox access where the feature allows it.
- Every integration connection is visibly listed in Settings and can be disconnected by an Admin or Owner at any time, immediately revoking our access.

**What we don't yet have (stated plainly, not hidden):**
- We do not yet hold a SOC 2 or equivalent third-party security certification. This is planned for a later stage of the company (once the product and customer base are mature enough to justify the audit), not because it isn't taken seriously now — encryption, access control, and scope minimization above are the concrete practices in place in the meantime.

---

## 2. "What happens to my data if I stop using NeuronOS?"

- Deleting a record (a customer, a document, a project) marks it for deletion but keeps it recoverable for 30 days, in case of an accidental delete — after that window, it is permanently purged.
- Disconnecting an integration immediately revokes NeuronOS's access token with that provider. Data already synced before disconnection remains in NeuronOS (tagged with which integration it came from) unless you separately request its deletion — disconnecting the integration does not automatically delete historical data pulled in while it was connected.
- A full account deletion (Settings → Danger Zone) is a deliberate, explicitly confirmed action — not a single click — and permanently removes the organization's data according to the same retention window as above.
- We do not sell or share your business data with third parties for any purpose outside operating the product itself (e.g., calling an LLM provider's API to generate a summary you requested is part of operating the product; selling your customer list to a third party is not something we do).

---

## 3. "Who's responsible if the AI sends something wrong?"

This is the question every business connecting an AI system that can act on their behalf should ask, and we'd rather answer it directly than leave it ambiguous.

**The core design principle:** NeuronOS is built so that no financially or relationally significant action — sending a contract-related email, generating an invoice — executes without a specific human explicitly approving that specific action (see our approve-first design, covered in the Master Blueprint). For these higher-stakes actions, NeuronOS drafts and recommends; the human who clicks "approve" is the one who decided to send it, in the same way a human deciding to send an email they drafted themselves is responsible for having sent it.

**For lower-stakes automations that a business has explicitly advanced to run without per-instance review** (e.g., a routine follow-up reminder, after a track record of correct suggestions), the organization's Owner or Admin who advanced that automation to run unsupervised is the one who made that deliberate choice — it's logged, and it's a choice the business made, not something NeuronOS did on its own initiative.

**In short:** our design goal is that a human always makes the meaningful decision for anything that matters — NeuronOS's job is to make that decision fast and well-informed, not to make it instead of you.

*(This section states the product's design intent. Final, binding liability language belongs in the actual Terms of Service, reviewed by qualified legal counsel — this document is the starting point for that language, not a replacement for it.)*

---

## 4. "Can we sign a Data Processing Agreement (DPA)?"

Yes — we don't have every customer on one yet (most early design partners haven't asked, and we don't push it prematurely), but a standard DPA is something we can put in front of you on request rather than something we need weeks to draft from scratch when asked. If your organization has its own compliance obligations that require one, tell us and we'll get it in front of you.

---

## 5. "What third parties do you send our data to?"

NeuronOS uses large language model providers (for example, Anthropic's Claude, and potentially others depending on the task) to generate summaries, drafts, and recommendations from your data. This means relevant snippets of your business data (a document excerpt, a customer's recent activity) are sent to these providers as part of generating a response — this is inherent to how the product works, not an optional add-on. We also use standard cloud infrastructure providers for hosting, storage, and background processing. A full list of sub-processors is available on request and will be a standard part of any DPA.

---

## 6. "Is our data used to train your AI models or anyone else's?"

Our default posture is that customer data is used to serve that customer — not pooled to train models for other customers or shared back to model providers for their own training purposes beyond what's needed to generate your response. (This section should be verified and made precise against the actual data-use terms of whichever LLM provider(s) are in use at the time this is shared with a customer — provider terms do change, and this statement should be kept current rather than assumed.)

---

## 7. Where This Stands Today vs. Where It's Headed

| Area | Today | Planned |
|---|---|---|
| Encryption, access control, scope minimization | ✅ In place | Ongoing hardening |
| SOC 2 / formal certification | ❌ Not yet | Phase 3+/Enterprise phase |
| Standard DPA available on request | ✅ Available | Formalized self-serve process later |
| GDPR-aligned data export/deletion | ✅ Designed in from the start | Formal compliance program later |
| Liability terms for AI-executed actions | ✅ Design intent stated here | Final legal-reviewed ToS language |

This table should be updated and re-shared as things change — a stale version of this document is worse than none, since it can misrepresent the actual current state to a customer relying on it.
