import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_action import ActionTypeRegistry, AIAction
from app.models.automation import Automation, AutomationRun
from app.repositories.automation_repository import AutomationRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.automation import AutomationCreate, AutomationUpdate, PromoteModeRequest

# Roadmap Phase 1's exact three canned templates ("follow-up reminder, invoice overdue,
# welcome new client"). `invoice_overdue` has no real invoice entity to evaluate against
# (Database Spec has no `invoices` table — see Reports' same honest gap, reports_service.py)
# and is approximated via deals past their expected close date, documented in
# `_find_invoice_overdue_matches` below rather than silently pretended to be exact.
CANNED_TEMPLATES = [
    {
        "key": "follow_up_no_reply",
        "name": "Follow up if no reply in 3 days",
        "trigger_type": "no_reply_days",
        "trigger_config": {"days": 3},
        "action_type": "send_followup_email",
        "action_config": {},
    },
    {
        "key": "invoice_overdue_reminder",
        "name": "Invoice overdue reminder",
        "trigger_type": "invoice_overdue",
        "trigger_config": {},
        "action_type": "send_invoice_reminder",
        "action_config": {},
    },
    {
        "key": "welcome_new_client",
        "name": "Welcome new client",
        "trigger_type": "new_customer",
        "trigger_config": {"within_hours": 24},
        "action_type": "send_followup_email",
        "action_config": {},
    },
]


class AutomationError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AutomationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._automations = AutomationRepository(session)
        self._customers = CustomerRepository(session)

    async def create(self, *, organization_id: uuid.UUID, data: AutomationCreate) -> Automation:
        automation = Automation(
            organization_id=organization_id,
            name=data.name,
            mode="dry_run",  # Always — never client-controlled (Blueprint §2.3's hard rule).
            is_active=data.is_active,
            trigger_type=data.trigger_type,
            trigger_config=data.trigger_config,
            action_type=data.action_type,
            action_config=data.action_config,
        )
        self._automations.add(automation)
        await self._session.flush()
        return automation

    async def list_automations(self) -> list[Automation]:
        return await self._automations.list_all()

    async def get(self, automation_id: uuid.UUID) -> Automation:
        automation = await self._automations.get_by_id(automation_id)
        if automation is None:
            raise AutomationError("not_found", "Automation not found.", 404)
        return automation

    async def update(self, automation_id: uuid.UUID, data: AutomationUpdate) -> Automation:
        automation = await self.get(automation_id)
        if data.is_active is not None:
            automation.is_active = data.is_active
        if data.name is not None:
            automation.name = data.name
        return automation

    async def promote_mode(self, automation_id: uuid.UUID, data: PromoteModeRequest) -> Automation:
        automation = await self.get(automation_id)
        # API Spec §8 — manually promoting straight to `live` without having earned it
        # through `graduating` is an explicit override, not a casual toggle, so it
        # requires a non-empty reason to force a deliberate decision to be recorded.
        bypassing_threshold = data.mode == "live" and (
            automation.mode != "graduating"
            or automation.approved_run_count < automation.graduation_threshold
        )
        if bypassing_threshold and not (data.reason and data.reason.strip()):
            raise AutomationError(
                "validation_error",
                "Promoting to live before the graduation threshold is reached requires a non-empty reason.",
                422,
            )
        automation.mode = data.mode
        return automation

    async def get_dry_run_results(self, automation_id: uuid.UUID, *, limit: int) -> list[AutomationRun]:
        await self.get(automation_id)  # 404 if missing/wrong org
        return await self._automations.list_runs(automation_id, status="simulated", limit=limit)

    async def get_runs(self, automation_id: uuid.UUID, *, limit: int) -> list[AutomationRun]:
        await self.get(automation_id)
        return await self._automations.list_runs(automation_id, limit=limit)

    # --- Trigger evaluation -----------------------------------------------------------

    async def _find_no_reply_matches(self, days: int, now: datetime) -> list[tuple[str, uuid.UUID]]:
        customers = await self._customers.list_all_active()
        matches = []
        for c in customers:
            reference = c.last_contact_at or c.created_at
            if reference.tzinfo is None:
                reference = reference.replace(tzinfo=timezone.utc)
            if (now - reference).days >= days:
                matches.append(("customer", c.id))
        return matches

    async def _find_new_customer_matches(self, within_hours: int, now: datetime) -> list[tuple[str, uuid.UUID]]:
        customers = await self._customers.list_all_active()
        matches = []
        for c in customers:
            created = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)
            if now - created <= timedelta(hours=within_hours):
                matches.append(("customer", c.id))
        return matches

    async def _find_invoice_overdue_matches(self, now: datetime) -> list[tuple[str, uuid.UUID]]:
        """Approximated via deals past their expected close date and still open — no
        `invoices` entity exists in this schema (see reports_service.py's identical
        gap note). Honest about what it actually checks, not a real invoice ledger."""
        deals = await self._customers.get_all_deals_for_org()
        return [
            ("deal", d.id)
            for d in deals
            if d.stage in ("proposal", "negotiation")
            and d.expected_close_date is not None
            and d.expected_close_date < now.date()
        ]

    async def evaluate_organization(
        self, *, organization_id: uuid.UUID, now: datetime
    ) -> list[AutomationRun]:
        """Runs every active automation's trigger check against current data — Phase 1
        has no scheduler (Blueprint §8, same reasoning as decision_engine.py), so this is
        invoked at meaningful synchronous points rather than on a cron. Idempotency here
        is deliberately coarse for Phase 1: one run per (automation, target entity) ever,
        not re-fired every time this is called for a target that already matched — a
        finer time-windowed re-trigger policy is left for when a real scheduler exists."""
        automations = await self._automations.list_active_org_automations()
        created_runs: list[AutomationRun] = []
        for automation in automations:
            created_runs.extend(
                await self.evaluate_single(automation, organization_id=organization_id, now=now)
            )
        return created_runs

    async def evaluate_single(
        self, automation: Automation, *, organization_id: uuid.UUID, now: datetime
    ) -> list[AutomationRun]:
        """API Spec §0.5 references `POST /automations/{id}/dry-run` as an
        idempotency-key-bearing endpoint, but §8's endpoint list never actually defined
        it — a gap between the two sections, not just a documentation nicety, since
        there was genuinely no way to make one specific automation check its trigger
        against real data on demand. Formalized as `POST /automations/{id}/evaluate`
        (API Spec §8) rather than reusing the name `dry-run`, since that would collide
        conceptually with the already-existing `GET .../dry-run-results` (a noun,
        viewing past runs) right next to a new verb of almost the same name — and
        because what this does depends on the automation's current mode, not only
        simulating."""
        if automation.mode == "paused":
            return []

        if automation.trigger_type == "no_reply_days":
            matches = await self._find_no_reply_matches(
                automation.trigger_config.get("days", 3), now
            )
        elif automation.trigger_type == "new_customer":
            matches = await self._find_new_customer_matches(
                automation.trigger_config.get("within_hours", 24), now
            )
        elif automation.trigger_type == "invoice_overdue":
            matches = await self._find_invoice_overdue_matches(now)
        else:
            # project_completed / contract_expiring: no backing data exists yet
            # (Projects is Phase 2 scope) — a registered, valid trigger_type that
            # simply never matches anything in Phase 1, not an error.
            matches = []

        created_runs: list[AutomationRun] = []
        for target_entity_type, target_entity_id in matches:
            idempotency_key = f"{automation.trigger_type}:{target_entity_id}"
            existing = await self._automations.get_run_by_idempotency_key(
                automation.id, idempotency_key
            )
            if existing is not None:
                continue

            run = await self._fire(
                automation,
                organization_id=organization_id,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                idempotency_key=idempotency_key,
                now=now,
            )
            created_runs.append(run)

        return created_runs

    async def _fire(
        self,
        automation: Automation,
        *,
        organization_id: uuid.UUID,
        target_entity_type: str,
        target_entity_id: uuid.UUID,
        idempotency_key: str,
        now: datetime,
    ) -> AutomationRun:
        automation.times_triggered += 1

        if automation.mode == "dry_run":
            run = AutomationRun(
                automation_id=automation.id,
                idempotency_key=idempotency_key,
                triggered_at=now,
                status="simulated",
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
            )
            self._automations.add_run(run)
            await self._session.flush()
            return run

        # graduating and live both create a real, visible record of what happened —
        # graduating routes it through human review first (API Spec §8's exact
        # "every real trigger creates a normal AI Action" behavior); live records it as
        # already executed (Phase 1 simplification: no external send channel exists yet,
        # same reasoning as ai_action_service.py's approve()).
        result = await self._session.execute(
            select(ActionTypeRegistry).where(ActionTypeRegistry.action_type == automation.action_type)
        )
        registry_entry = result.scalar_one()

        action = AIAction(
            organization_id=organization_id,
            title=f"{automation.name} ({target_entity_type})",
            description=None,
            action_type=automation.action_type,
            severity_tier=registry_entry.severity_tier,
            is_reversible=registry_entry.is_reversible,
            reasoning=f"Automation '{automation.name}' matched: {target_entity_type} {target_entity_id}.",
            confidence_score=None,
            priority="medium",
            status="suggested" if automation.mode == "graduating" else "executed",
            related_entity_type="automation",
            related_entity_id=automation.id,
            generated_by_engine="automation",
        )
        if automation.mode == "live":
            action.decided_at = now
            action.executed_at = now
        self._session.add(action)
        await self._session.flush()

        run = AutomationRun(
            automation_id=automation.id,
            idempotency_key=idempotency_key,
            triggered_at=now,
            status="pending_approval" if automation.mode == "graduating" else "success",
            related_ai_action_id=action.id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
        )
        self._automations.add_run(run)

        if automation.mode == "live":
            successes = await self._automations.list_runs(automation.id, status="success", limit=10000)
            automation.success_rate_pct = round(len(successes) / automation.times_triggered * 100)

        await self._session.flush()
        return run
