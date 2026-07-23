import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.settings import RequestDpaRequest, UpdateMemberRequest, UpdateOrganizationRequest

logger = logging.getLogger(__name__)

# API Spec §10 — every provider NeuronOS plans to support, shown even when no
# organization has connected one yet, so Settings' Integrations tab has something
# real and accurate to render ("not connected" is real data, not a placeholder).
SUPPORTED_PROVIDERS = (
    "gmail",
    "google_drive",
    "google_calendar",
    "outlook",
    "microsoft_365",
    "slack",
    "whatsapp",
    "hubspot",
    "salesforce",
    "zoho_crm",
    "zoho_books",
    "quickbooks",
)


class SettingsError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._organizations = OrganizationRepository(session)
        self._users = UserRepository(session)

    async def update_organization(
        self, organization_id: uuid.UUID, data: UpdateOrganizationRequest
    ) -> Organization:
        organization = await self._organizations.get_by_id(organization_id)
        assert organization is not None
        if data.name is not None:
            organization.name = data.name
        if data.industry is not None:
            organization.industry = data.industry
        if data.company_size is not None:
            organization.company_size = data.company_size
        if data.timezone is not None:
            organization.timezone = data.timezone
        return organization

    async def list_members(self) -> list[User]:
        return await self._users.list_for_organization()

    async def update_member(self, user_id: uuid.UUID, data: UpdateMemberRequest, *, acting_user: User) -> User:
        member = await self._users.get_by_id(user_id)
        if member is None:
            raise SettingsError("not_found", "Member not found.", 404)

        if data.role is not None:
            if acting_user.role not in ("owner", "admin"):
                raise SettingsError("permission_denied", "Requires Admin or Owner.", 403)
            if member.role == "owner":
                raise SettingsError(
                    "validation_error", "Ownership is transferred through a separate flow.", 422
                )
            member.role = data.role

        if data.status is not None:
            if acting_user.role != "owner":
                raise SettingsError("permission_denied", "Only the Owner can change member status.", 403)
            if data.status == "suspended" and member.role == "owner":
                raise SettingsError(
                    "validation_error", "The sole Owner cannot be suspended.", 422
                )
            member.status = data.status

        return member

    async def request_dpa(self, *, organization_id: uuid.UUID, data: RequestDpaRequest) -> None:
        """API Spec §11 — 'MVP implementation can be as simple as creating an internal
        notification/ticket.' Structured logging (Blueprint §15) is exactly that at
        Phase 1 scale: it reaches the team (via whatever log aggregation is already
        watched) without standing up a ticketing integration for a rare request."""
        logger.info(
            "DPA requested for organization %s (requested_by_email=%s, notes=%s)",
            organization_id,
            data.requested_by_email,
            data.notes,
        )

    async def list_integrations(self) -> list[dict]:
        return [
            {
                "provider": provider,
                "status": "not_connected",
                "provider_review_status": "not_submitted",
                "last_synced_at": None,
            }
            for provider in SUPPORTED_PROVIDERS
        ]
