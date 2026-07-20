from datetime import datetime

from sqlalchemy import CheckConstraint, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, SoftDeleteMixin, UpdatedAtMixin, UUIDPKMixin


class Organization(UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin, SoftDeleteMixin, Base):
    """Database Spec §1.1. Hard-deleted only via the explicit Settings → Danger Zone →
    Delete Account flow (API Spec §11) — soft delete otherwise, like every other table."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "company_size IN ('1-10','11-50','51-250','251+')", name="company_size_valid"
        ),
        CheckConstraint(
            "plan IN ('trial','starter','growth','enterprise')", name="plan_valid"
        ),
        CheckConstraint(
            "onboarding_method IN ('integration','documents','manual_customers')",
            name="onboarding_method_valid",
        ),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_size: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="trial")
    business_health_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    score_algorithm_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="v1_rule_based"
    )

    # Cold-start onboarding state (Database Spec §1.3 / Onboarding Spec)
    onboarding_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    onboarding_first_insight_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Terms / DPA (Database Spec §1.1, Blueprint §17.8/§17.9)
    terms_accepted_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    dpa_signed_at: Mapped[datetime | None] = mapped_column(nullable=True)
