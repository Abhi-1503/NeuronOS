"""Importing this package registers every model on `Base.metadata`, which is what the
Alembic migration (and `Base.metadata.create_all` in tests) uses to know the full schema.
Every model module must be imported here — a model defined but not imported is invisible
to Alembic autogenerate and to the test database setup."""

from app.models.ai_action import ActionTypeRegistry, AIAction, AIActionExecution
from app.models.automation import Automation, AutomationRun
from app.models.base import Base
from app.models.customer import Customer, Deal, TimelineEvent
from app.models.document import Document, DocumentChunk, DocumentTag, LinkedEntity
from app.models.integration import IntegrationConnection
from app.models.meeting import Meeting, MeetingActionItem, MeetingAttendee, MeetingSummary
from app.models.organization import Organization
from app.models.project import Project, ProjectMember, RiskFlag, Task
from app.models.score_history import ScoreHistory
from app.models.user import User

__all__ = [
    "Base",
    "Organization",
    "User",
    "Customer",
    "TimelineEvent",
    "Deal",
    "Project",
    "ProjectMember",
    "Task",
    "RiskFlag",
    "Meeting",
    "MeetingAttendee",
    "MeetingSummary",
    "MeetingActionItem",
    "Document",
    "DocumentChunk",
    "DocumentTag",
    "LinkedEntity",
    "Automation",
    "AutomationRun",
    "ActionTypeRegistry",
    "AIAction",
    "AIActionExecution",
    "ScoreHistory",
    "IntegrationConnection",
]
