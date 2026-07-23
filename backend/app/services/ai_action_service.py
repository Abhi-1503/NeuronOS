import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_action import AIAction, AIActionExecution
from app.models.user import User
from app.repositories.ai_action_repository import AIActionRepository
from app.repositories.automation_repository import AutomationRepository
from app.schemas.ai_action import ApproveRequest, RejectRequest


class AIActionError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AIActionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AIActionRepository(session)
        self._automations = AutomationRepository(session)

    async def get(self, action_id: uuid.UUID) -> AIAction:
        action = await self._repo.get_by_id(action_id)
        if action is None:
            raise AIActionError("not_found", "AI Action not found.", 404)
        return action

    async def list_actions(
        self, *, status: str | None, assigned_to_user_id: uuid.UUID | None, cursor, limit: int
    ) -> list[AIAction]:
        return await self._repo.list(
            status=status, assigned_to_user_id=assigned_to_user_id, cursor=cursor, limit=limit
        )

    def _check_can_decide(self, action: AIAction, user: User) -> None:
        if user.role in ("owner", "admin"):
            return
        if user.id in (action.assigned_to_user_id, action.delegated_to_user_id):
            return
        raise AIActionError(
            "permission_denied",
            "You do not have permission to act on this AI Action.",
            403,
        )

    async def approve(
        self,
        action_id: uuid.UUID,
        *,
        user: User,
        idempotency_key: str,
        body: ApproveRequest,
    ) -> AIAction:
        # Idempotency (API Spec §0.5): a replayed request with the same key returns the
        # already-executed result rather than re-approving/re-executing — checked before
        # touching the action at all, so a retry after a network blip can't double-fire.
        existing_execution = await self._repo.get_execution_by_idempotency_key(idempotency_key)
        if existing_execution is not None:
            return await self.get(existing_execution.ai_action_id)

        action = await self.get(action_id)
        self._check_can_decide(action, user)

        if action.status != "suggested":
            raise AIActionError(
                "conflict", f"This action is already {action.status}, not suggested.", 409
            )

        if action.severity_tier == "high" and body.confirm_high_severity is not True:
            raise AIActionError(
                "validation_error",
                "High-severity actions require confirm_high_severity: true.",
                422,
            )

        now = datetime.now(timezone.utc)
        action.status = "approved"
        action.decided_by_user_id = user.id
        action.decided_at = now
        # `body.edited_content`, if provided, is recorded on the execution row below as
        # the executed payload — not written back onto `description`, which stays the
        # historical record of what was originally suggested.

        # No Celery/external send channel exists yet (Blueprint §8 — Phase 1 has no
        # background runner wired up, and there's no live email-sending integration
        # until Phase 2). "Execution" for Phase 1 is: mark it done and record what the
        # user approved, so they can act on the drafted content themselves — consistent
        # with the product being usable with zero integrations connected (Blueprint §4.3).
        action.status = "executed"
        action.executed_at = now

        self._repo.add_execution(
            AIActionExecution(
                ai_action_id=action.id,
                idempotency_key=idempotency_key,
                executed_action=action.action_type,
                payload=body.edited_content,
                result="success",
                executed_at=now,
            )
        )

        # API Spec §7's approve behavior: an approval on an action that originated from
        # a `graduating`-mode automation counts toward that automation's graduation —
        # once it reaches `graduation_threshold`, the automation is promoted to `live`
        # automatically (surfaced to the user as a notification per the spec; no
        # notification channel exists yet in Phase 1, so this only updates the state —
        # flagged here rather than silently claimed as fully implemented).
        if action.related_entity_type == "automation" and action.related_entity_id is not None:
            automation = await self._automations.get_by_id(action.related_entity_id)
            if automation is not None and automation.mode == "graduating":
                automation.approved_run_count += 1
                if automation.approved_run_count >= automation.graduation_threshold:
                    automation.mode = "live"

        await self._session.flush()
        return action

    async def reject(self, action_id: uuid.UUID, *, user: User, body: RejectRequest) -> AIAction:
        action = await self.get(action_id)
        self._check_can_decide(action, user)
        if action.status != "suggested":
            raise AIActionError(
                "conflict", f"This action is already {action.status}, not suggested.", 409
            )
        # `body.reason` feeds the Learning Engine (API Spec §7) — not built yet (Phase 2+,
        # Blueprint §14), and `ai_actions` has no column to persist a rejection reason on
        # (Database Spec §7.1). Accepted per the documented contract; not silently
        # dropped without acknowledgment, but genuinely not persisted anywhere yet.
        action.status = "rejected"
        action.decided_by_user_id = user.id
        action.decided_at = datetime.now(timezone.utc)

        # API Spec §7's reject behavior: a rejection on a `graduating`-mode automation's
        # action resets its approved_run_count to 0 — a rejection is a signal the
        # trigger/action logic needs revisiting, not just a delay to graduation.
        if action.related_entity_type == "automation" and action.related_entity_id is not None:
            automation = await self._automations.get_by_id(action.related_entity_id)
            if automation is not None and automation.mode == "graduating":
                automation.approved_run_count = 0

        await self._session.flush()
        return action

    async def delegate(self, action_id: uuid.UUID, *, user: User, delegated_to_user_id: uuid.UUID) -> AIAction:
        action = await self.get(action_id)
        if user.role not in ("owner", "admin") and user.id != action.assigned_to_user_id:
            raise AIActionError(
                "permission_denied", "Only the assignee, Admin, or Owner can delegate this.", 403
            )
        action.status = "delegated"
        action.delegated_to_user_id = delegated_to_user_id
        await self._session.flush()
        return action
