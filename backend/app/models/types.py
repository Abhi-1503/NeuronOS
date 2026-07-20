from sqlalchemy.types import UserDefinedType


class CIText(UserDefinedType):
    """Postgres `citext` — case-insensitive text, used for `users.email` (Database Spec §1.2)
    and `meeting_attendees.customer_contact_email` (§4.2). Not a built-in SQLAlchemy type
    (unlike UUID/JSONB/ARRAY), so it's defined directly against the `citext` extension rather
    than depending on a third-party package. The `citext` extension itself is enabled in the
    first Alembic migration."""

    cache_ok = True

    def get_col_spec(self, **kw) -> str:
        return "CITEXT"
