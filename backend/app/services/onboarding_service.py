import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ai_action_repository import AIActionRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.onboarding import (
    FirstInsightOut,
    OnboardingCompleteOut,
    OnboardingStatusOut,
    OnboardingStep,
)
from app.services.decision_engine import DecisionEngine

VALID_METHODS = ("integration", "documents", "manual_customers")

# Minimum data needed for "enough for a real insight" (API Spec §5B's
# `POST /onboarding/complete` note; exact threshold flagged as an open item needing real
# usage data — Onboarding Spec §7 item 1, API Spec Open Items #13). One customer is the
# concrete threshold chosen for Phase 1 — it's the smallest amount of data the Decision
# Engine can meaningfully reason about at all.
MIN_CUSTOMERS_FOR_COMPLETION = 1


class OnboardingError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class OnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._organizations = OrganizationRepository(session)
        self._customers = CustomerRepository(session)
        self._ai_actions = AIActionRepository(session)
        self._decision_engine = DecisionEngine(session)

    def _build_steps(self, *, method: str | None, customer_count: int, first_insight_at) -> list[OnboardingStep]:
        return [
            OnboardingStep(
                key="select_method", label="Choose how to get started", completed=method is not None
            ),
            OnboardingStep(
                key="add_data",
                label="Add your top customers",
                completed=customer_count >= MIN_CUSTOMERS_FOR_COMPLETION,
            ),
            OnboardingStep(
                key="first_insight",
                label="Get your first insight",
                completed=first_insight_at is not None,
            ),
        ]

    async def get_status(self, organization_id: uuid.UUID) -> OnboardingStatusOut:
        organization = await self._organizations.get_by_id(organization_id)
        assert organization is not None
        customer_count = await self._customers.count_active()
        return OnboardingStatusOut(
            onboarding_method=organization.onboarding_method,
            steps=self._build_steps(
                method=organization.onboarding_method,
                customer_count=customer_count,
                first_insight_at=organization.onboarding_first_insight_at,
            ),
            first_insight_at=organization.onboarding_first_insight_at,
        )

    async def select_method(self, organization_id: uuid.UUID, method: str) -> OnboardingStatusOut:
        if method not in VALID_METHODS:
            raise OnboardingError(
                "validation_error", f"method must be one of {VALID_METHODS}.", 422
            )
        organization = await self._organizations.get_by_id(organization_id)
        assert organization is not None
        organization.onboarding_method = method
        await self._session.flush()
        return await self.get_status(organization_id)

    async def complete(self, organization_id: uuid.UUID) -> OnboardingCompleteOut:
        organization = await self._organizations.get_by_id(organization_id)
        assert organization is not None

        customer_count = await self._customers.count_active()
        if customer_count < MIN_CUSTOMERS_FOR_COMPLETION:
            raise OnboardingError(
                "validation_error",
                f"Add at least {MIN_CUSTOMERS_FOR_COMPLETION} customer before completing onboarding.",
                422,
            )

        now = datetime.now(timezone.utc)
        organization.onboarding_completed_at = now

        first_insight: FirstInsightOut | None = None
        is_first_time = organization.onboarding_first_insight_at is None

        if is_first_time:
            await self._decision_engine.run_for_organization(
                organization_id=organization_id, now=now
            )
            organization.onboarding_first_insight_at = now
            # Deliberately re-queried after the pass rather than using its returned list —
            # a customer added via `POST /customers` earlier in the session may already
            # have been flagged at creation time (CustomerService.create), in which case
            # this pass generates nothing *new* for it but a real, already-existing risk
            # flag still exists. Checking "what actually exists now" is what's correct
            # here, not "what this one call happened to create."
            existing_suggested = await self._ai_actions.list(
                status="suggested", assigned_to_user_id=None, cursor=None, limit=1
            )
            if existing_suggested:
                action = existing_suggested[0]
                first_insight = FirstInsightOut(
                    type="risk_flag", message=action.reasoning or action.title, ai_action_id=action.id
                )
            else:
                # The honest "nothing's wrong" case (Onboarding Spec §3.3) — a correct
                # all-clear is a real insight, not a failure to produce one. Never
                # fabricate a risk here just to have something to show.
                first_insight = FirstInsightOut(
                    type="all_clear",
                    message=(
                        f"All {customer_count} customer{'s' if customer_count != 1 else ''} you "
                        f"added look recently contacted — nothing needs attention right now. As "
                        f"you add more data, I'll start catching things you'd otherwise miss."
                    ),
                    ai_action_id=None,
                )

        await self._session.flush()
        status = await self.get_status(organization_id)
        return OnboardingCompleteOut(
            onboarding_method=status.onboarding_method,
            steps=status.steps,
            first_insight_at=status.first_insight_at,
            first_insight=first_insight,
        )
