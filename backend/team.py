"""
Teams for M-AIDA 8.0: a shared workspace that belongs to one owner.

The owner invites people by e-mail (only addresses on the closed-beta list,
MAIDA_INVITED_EMAILS). An invitation becomes a membership the first time that
address signs in and opens the owner's workspace. Inside it:

* the records and jobs are the owner's (``owner_id`` = the owner), so nothing
  moves when someone joins or leaves;
* a member uploads PDFs and the owner's credits pay for them;
* a member verifies records (approve, correct, flag);
* only the owner locks records, deletes them, exports and edits the PRISMA
  counts.

The browser chooses the workspace per request with the ``X-MAIDA-Workspace``
header (the owner's account id); no header means the caller's own
workspace. main.py turns that into a :class:`Workspace` for every route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import sessionmaker

from db import TeamMember, User, utcnow
from settings import Settings

#: People an owner can invite (not counting the owner).
MAX_MEMBERS = 10

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Workspace:
    """Where a request acts: whose records, whose credits, and as whom."""

    owner_id: str
    owner_email: str
    actor_id: str
    actor_email: str

    @property
    def is_owner(self) -> bool:
        return self.owner_id == self.actor_id

    @property
    def role(self) -> str:
        return "owner" if self.is_owner else "member"

    def require_owner(self, action: str) -> None:
        if not self.is_owner:
            raise HTTPException(
                status_code=403,
                detail=f"owner_only: only the workspace owner can {action}.",
            )


class TeamService:
    def __init__(self, session_factory: sessionmaker, settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    # -- owner side ------------------------------------------------------------

    def members(self, owner_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as s:
            rows = s.scalars(
                select(TeamMember).where(TeamMember.owner_id == owner_id).order_by(TeamMember.created_at, TeamMember.id)
            ).all()
            names = {u.id: u.name for u in s.scalars(
                select(User).where(User.id.in_([r.member_id for r in rows if r.member_id]))
            ).all()} if rows else {}
        return [
            {"email": r.email, "member_id": r.member_id, "name": names.get(r.member_id or "", ""),
             "invited_at": r.created_at, "joined_at": r.joined_at,
             "status": "active" if r.member_id else "invited"}
            for r in rows
        ]

    def invite(self, owner_id: str, owner_email: str, email: str) -> dict[str, Any]:
        email = (email or "").strip().lower()
        if not _EMAIL.match(email):
            raise HTTPException(status_code=422, detail="Enter one e-mail address.")
        if email == (owner_email or "").lower():
            raise HTTPException(status_code=422, detail="You are already the owner of this workspace.")
        if not self.settings.is_invited(email):
            raise HTTPException(
                status_code=422,
                detail="not_invited: this address is not on the closed-beta list (MAIDA_INVITED_EMAILS). "
                       "Ask the operator to add it first.",
            )
        with self.session_factory() as s:
            exists = s.scalar(select(TeamMember.id).where(TeamMember.owner_id == owner_id, TeamMember.email == email))
            if exists is not None:
                raise HTTPException(status_code=409, detail="This address is already in your team.")
            count = s.scalar(select(func.count()).select_from(TeamMember).where(TeamMember.owner_id == owner_id)) or 0
            if count >= MAX_MEMBERS:
                raise HTTPException(status_code=422, detail=f"A team has at most {MAX_MEMBERS} members.")
            # The invitation turns into a membership when that address first
            # opens the workspace (resolve), whether or not it has an account yet.
            s.add(TeamMember(owner_id=owner_id, email=email, member_id=None, created_at=utcnow()))
            s.commit()
        return next(m for m in self.members(owner_id) if m["email"] == email)

    def remove(self, owner_id: str, email: str) -> None:
        email = (email or "").strip().lower()
        with self.session_factory() as s:
            row = s.scalar(select(TeamMember).where(TeamMember.owner_id == owner_id, TeamMember.email == email))
            if row is None:
                raise HTTPException(status_code=404, detail="Not in your team.")
            s.delete(row)
            s.commit()

    # -- member side -----------------------------------------------------------

    def _mine(self, user_id: str, email: str):
        email = (email or "").strip().lower()
        cond = TeamMember.member_id == user_id
        if email:
            cond = or_(cond, (TeamMember.member_id.is_(None)) & (TeamMember.email == email))
        return cond

    def memberships(self, user_id: str, email: str) -> list[dict[str, Any]]:
        with self.session_factory() as s:
            rows = s.execute(
                select(TeamMember, User).join(User, User.id == TeamMember.owner_id)
                .where(self._mine(user_id, email), TeamMember.owner_id != user_id)
                .order_by(TeamMember.created_at)
            ).all()
        return [
            {"owner_id": t.owner_id, "owner_email": u.email, "owner_name": u.name,
             "invited_at": t.created_at, "joined_at": t.joined_at,
             "status": "active" if t.member_id else "invited"}
            for t, u in rows
        ]

    def leave(self, owner_id: str, user_id: str, email: str) -> None:
        with self.session_factory() as s:
            row = s.scalar(select(TeamMember).where(TeamMember.owner_id == owner_id, self._mine(user_id, email)))
            if row is None:
                raise HTTPException(status_code=404, detail="You are not in this team.")
            s.delete(row)
            s.commit()

    def resolve(self, owner_id: str, user_id: str, email: str) -> Workspace:
        """The workspace ``owner_id`` for this caller, or 403 if they are not in its team."""
        with self.session_factory() as s:
            row = s.scalar(select(TeamMember).where(TeamMember.owner_id == owner_id, self._mine(user_id, email)))
            owner = s.get(User, owner_id)
            if row is None or owner is None:
                raise HTTPException(
                    status_code=403,
                    detail="not_member: you are not a member of this workspace (any more).",
                )
            if row.member_id is None:  # first visit: the invitation becomes a membership
                row.member_id = user_id
                row.joined_at = utcnow()
                s.commit()
            owner_email = owner.email
        return Workspace(owner_id=owner_id, owner_email=owner_email, actor_id=user_id, actor_email=email)
