import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_action import AIAction
from app.models.customer import Customer
from app.models.score_history import ScoreHistory
from app.repositories.ai_action_repository import AIActionRepository
from app.repositories.customer_repository import CustomerRepository

SCORE_ALGORITHM_VERSION = "v1_rule_based"

# Illustrative default from Onboarding Spec §7 open item 1 — "starting points, not
# validated numbers." Tune against real early-user data once it exists; not hardcoded
# anywhere else so this is the one place to change it.
STALE_CONTACT_THRESHOLD_DAYS = 12

# Rule-based decay (Blueprint §14 — Decision Engine MVP is explicitly "recency, amount,
# keyword signals," not an ML model): 100 at day 0, floor 0, -3 points per day since
# last contact. A customer never contacted at all is scored from `created_at` instead of
# an undefined "days since None."
_SCORE_START = 100
_SCORE_DECAY_PER_DAY = 3


@dataclass
class DecisionResult:
    relationship_score: int
    days_since_contact: int
    should_flag: bool
    reasoning: str
    confidence_score: float


def _days_since(reference: datetime, now: datetime) -> int:
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0, (now - reference).days)


def evaluate_customer(customer: Customer, *, now: datetime) -> DecisionResult:
    """The actual rule (Blueprint §2.7 requires every conclusion to carry the real signal
    that produced it, not just a number) — this function is the single place that signal
    is computed, so `reasoning` and `relationship_score` can never drift apart."""
    reference = customer.last_contact_at or customer.created_at
    days_since = _days_since(reference, now)
    score = max(0, _SCORE_START - days_since * _SCORE_DECAY_PER_DAY)

    should_flag = days_since >= STALE_CONTACT_THRESHOLD_DAYS
    if customer.last_contact_at is None:
        reasoning = (
            f"No contact has been logged since this customer was added "
            f"{days_since} day{'s' if days_since != 1 else ''} ago."
        )
    else:
        reasoning = (
            f"No contact logged in {days_since} day{'s' if days_since != 1 else ''} "
            f"(last contact: {customer.last_contact_at.date().isoformat()})."
        )

    # Confidence here is a proxy for "how far past the threshold," not a calibrated
    # probability — this is a rule-based signal (Blueprint §14), and the confidence
    # field exists so a wrong call reads as "here's the signal, was I right?" rather
    # than an unexplained overconfident claim (Blueprint §2.7), not to imply ML-grade
    # calibration that doesn't exist yet.
    if should_flag:
        overshoot = days_since - STALE_CONTACT_THRESHOLD_DAYS
        confidence_score = min(0.95, 0.6 + overshoot * 0.03)
    else:
        confidence_score = 0.5

    return DecisionResult(
        relationship_score=score,
        days_since_contact=days_since,
        should_flag=should_flag,
        reasoning=reasoning,
        confidence_score=round(confidence_score, 2),
    )


def _draft_followup_email(customer: Customer, result: DecisionResult) -> str:
    """A deterministic template, not a live LLM call — Phase 1's Action Engine drafts
    with templates + context injection (Blueprint §14 MVP column) using a fixed skeleton
    rather than a real model call. Model Router / live generation is explicitly Phase 2
    (Blueprint §14.3), and calling a real LLM here before the unit-economics model has
    been checked against actual usage would be exactly the premature-cost risk Blueprint
    §1.9 warns about."""
    return (
        f"Hi {customer.name},\n\n"
        f"It's been {result.days_since_contact} days since we last connected — just "
        f"wanted to check in and see how things are going on your end. Let me know if "
        f"there's anything I can help with.\n\n"
        f"Best,"
    )


class DecisionEngine:
    """Rule-based Relationship Score + risk-flag AI Action generation (Blueprint §14,
    Onboarding Spec §3.2 Path C). Runs synchronously in-request — Phase 1 has no
    background job runner wired up yet (Celery/Redis, Blueprint §8), and nothing here
    talks to an external system, so there's no async work to actually defer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._ai_actions = AIActionRepository(session)

    async def evaluate_and_flag(
        self, customer: Customer, *, organization_id: uuid.UUID, now: datetime
    ) -> AIAction | None:
        """Recomputes one customer's score, records score history, and creates a new
        `suggested` AI Action if flagged — unless an unactioned one already exists for
        this customer (idempotent re-runs must not spam duplicate suggestions).

        Also auto-resolves the reverse case: if a customer was previously flagged and
        the signal that caused it no longer holds (e.g. a new contact event just came
        in), the stale `suggested` action is closed out rather than left sitting in the
        queue — showing a "you haven't followed up!" recommendation after the user
        already has is exactly the kind of stale-but-technically-not-wrong claim that
        erodes trust (Blueprint §2.7's concern, in the opposite direction from a false
        positive). Closed via the existing status vocabulary (`rejected`, with
        `decided_by_user_id` left `NULL` to distinguish "the system closed this because
        the signal changed" from an actual human rejection) — no new column needed.
        """
        result = evaluate_customer(customer, now=now)
        customer.relationship_score = result.relationship_score
        customer.score_algorithm_version = SCORE_ALGORITHM_VERSION

        self._session.add(
            ScoreHistory(
                organization_id=organization_id,
                entity_type="customer",
                entity_id=customer.id,
                score=result.relationship_score,
                algorithm_version=SCORE_ALGORITHM_VERSION,
                computed_at=now,
            )
        )

        existing = await self._ai_actions.get_latest_unactioned_for_entity(
            related_entity_type="customer", related_entity_id=customer.id
        )

        if not result.should_flag:
            if existing is not None:
                existing.status = "rejected"
                existing.decided_at = now
            return None

        if existing is not None:
            return None

        action = AIAction(
            organization_id=organization_id,
            title=f"Follow up with {customer.name}",
            description=_draft_followup_email(customer, result),
            action_type="send_followup_email",
            severity_tier="low",
            is_reversible=False,
            reasoning=result.reasoning,
            confidence_score=result.confidence_score,
            priority="medium",
            status="suggested",
            related_entity_type="customer",
            related_entity_id=customer.id,
            assigned_to_user_id=customer.owner_user_id,
            generated_by_engine="decision_engine_v1_rule_based",
        )
        self._ai_actions.add(action)
        await self._session.flush()
        return action

    async def run_for_organization(
        self, *, organization_id: uuid.UUID, now: datetime
    ) -> list[AIAction]:
        customers = await self._customers.list_active(limit=1000)
        generated: list[AIAction] = []
        for customer in customers:
            action = await self.evaluate_and_flag(customer, organization_id=organization_id, now=now)
            if action is not None:
                generated.append(action)
        return generated

    async def compute_business_health(
        self, *, organization_id: uuid.UUID, now: datetime
    ) -> int | None:
        """Business Health Score (Blueprint §1.2/Glossary) — the MVP rule-based proxy is
        the average of active customers' own relationship scores, since those are already
        computed from the same rule set (Blueprint §14's Decision Engine row explicitly
        covers both scores with one MVP implementation, not two separate models).
        `None` when the org has no customers yet — Pulse's cold-start state (§4.4) is
        what covers that case, not a fabricated number here. Recomputed synchronously on
        each read (`GET /organization`) rather than an overnight batch — Phase 1 has no
        background runner (Blueprint §8), and this is a cheap aggregate query, not an
        LLM call, so recomputing per-request isn't the cost concern the "don't recompute
        AI Summaries on every load" principle (Blueprint's Project Detail screen spec) is
        actually about.
        """
        customers = await self._customers.list_active(limit=1000)
        scored = [c.relationship_score for c in customers if c.relationship_score is not None]
        if not scored:
            return None
        score = round(sum(scored) / len(scored))
        self._session.add(
            ScoreHistory(
                organization_id=organization_id,
                entity_type="organization",
                entity_id=organization_id,
                score=score,
                algorithm_version=SCORE_ALGORITHM_VERSION,
                computed_at=now,
            )
        )
        return score
