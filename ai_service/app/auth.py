"""Who is calling, and what may they do?

The React shop already logs users in with Django REST Framework and keeps the token in localStorage.
We do NOT create a second login system: the assistant receives the same `Authorization: Token <key>`
header and looks the token up (read-only) in the shop database. The role comes from the database,
never from anything the user types.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models_store import Token, User

ROLES = ("anonymous", "customer", "staff", "admin")

# Which specialist agents each role may reach. Enforced in code (the model cannot override it).
AGENT_ACCESS: dict[str, frozenset[str]] = {
    "anonymous": frozenset({"support"}),
    "customer": frozenset({"support"}),
    "staff": frozenset({"support", "marketing", "analytics"}),
    "admin": frozenset({"support", "marketing", "analytics"}),
}


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class Principal:
    user_id: str | None
    email: str | None
    role: str  # one of ROLES

    @property
    def is_staff(self) -> bool:
        return self.role in ("staff", "admin")

    @property
    def allowed_agents(self) -> frozenset[str]:
        return AGENT_ACCESS[self.role]


ANONYMOUS = Principal(user_id=None, email=None, role="anonymous")


def resolve_principal(store: Session, authorization: str | None) -> Principal:
    """No header -> anonymous visitor. A header that is present but wrong -> AuthError (never silently downgraded)."""
    if not authorization:
        return ANONYMOUS
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "token":
        raise AuthError("Malformed Authorization header")
    row = store.execute(
        select(User).join(Token, Token.user_id == User.id).where(Token.key == parts[1])
    ).scalar_one_or_none()
    if row is None or not row.is_active:
        raise AuthError("Invalid or expired token")
    role = "admin" if row.is_superuser else (row.role if row.role in ("customer", "staff", "admin") else "customer")
    return Principal(user_id=row.id.hex, email=row.email, role=role)
