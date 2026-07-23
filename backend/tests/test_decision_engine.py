import uuid
from datetime import datetime, timedelta, timezone

from app.models.customer import Customer
from app.services.decision_engine import STALE_CONTACT_THRESHOLD_DAYS, evaluate_customer


def _customer(*, last_contact_at=None, created_at=None) -> Customer:
    now = datetime.now(timezone.utc)
    customer = Customer(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="ABC Ltd",
    )
    customer.created_at = created_at or now
    customer.last_contact_at = last_contact_at
    return customer


def test_recent_contact_is_not_flagged():
    now = datetime.now(timezone.utc)
    customer = _customer(last_contact_at=now - timedelta(days=1))
    result = evaluate_customer(customer, now=now)
    assert result.should_flag is False
    assert result.relationship_score > 90


def test_stale_contact_is_flagged_with_reasoning_citing_the_actual_date():
    now = datetime.now(timezone.utc)
    last_contact = now - timedelta(days=14)
    customer = _customer(last_contact_at=last_contact)
    result = evaluate_customer(customer, now=now)
    assert result.should_flag is True
    assert "14 day" in result.reasoning
    assert last_contact.date().isoformat() in result.reasoning


def test_exactly_at_threshold_is_flagged():
    now = datetime.now(timezone.utc)
    customer = _customer(last_contact_at=now - timedelta(days=STALE_CONTACT_THRESHOLD_DAYS))
    result = evaluate_customer(customer, now=now)
    assert result.should_flag is True


def test_never_contacted_uses_created_at_and_says_so():
    now = datetime.now(timezone.utc)
    customer = _customer(last_contact_at=None, created_at=now - timedelta(days=20))
    result = evaluate_customer(customer, now=now)
    assert result.should_flag is True
    assert "added" in result.reasoning
    assert "20 day" in result.reasoning


def test_score_never_goes_negative_for_very_stale_customers():
    now = datetime.now(timezone.utc)
    customer = _customer(last_contact_at=now - timedelta(days=365))
    result = evaluate_customer(customer, now=now)
    assert result.relationship_score == 0


def test_confidence_increases_the_further_past_threshold():
    now = datetime.now(timezone.utc)
    just_over = evaluate_customer(
        _customer(last_contact_at=now - timedelta(days=STALE_CONTACT_THRESHOLD_DAYS)), now=now
    )
    way_over = evaluate_customer(
        _customer(last_contact_at=now - timedelta(days=STALE_CONTACT_THRESHOLD_DAYS + 30)), now=now
    )
    assert way_over.confidence_score > just_over.confidence_score
    assert way_over.confidence_score <= 0.95
