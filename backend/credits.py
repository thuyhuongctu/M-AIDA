"""
Credit ledger for M-AIDA 8.x.

One credit = one extraction attempt that reached the language model. The
ledger (``credit_ledger``) is append-only and is the source of truth;
``users.credits_balance`` is a cache rewritten on every entry so the
dashboard can read one row.

Rules (decided 02/10/2026, see the v8 specification):

* A job reserves 1 credit when it is accepted (``extraction``); the user can
  therefore never queue more jobs than credits.
* A job that the model answered but the evidence gate or the format check
  rejected (HTTP 422 in 7.2 terms) keeps the charge: the provider billed the
  call and "no usable evidence in this paper" is itself a result.
* A job that failed for a reason on our side (provider error, timeout, PDF
  unreadable *after* acceptance, internal error) is refunded (``refund``).
* Balances never go below zero; a charge that would do so raises
  :class:`InsufficientCredits` and nothing is written.

Concurrency: the user's row is locked for the duration of the ledger write
(``SELECT ... FOR UPDATE`` on Postgres; SQLite serialises writers itself), so
two parallel charges cannot both read the same balance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from db import CreditLedger, User, utcnow

REASONS = frozenset({"purchase", "extraction", "refund", "grant_beta", "adjust_admin"})


class InsufficientCredits(Exception):
    """Raised when a charge would take the balance below zero."""


@dataclass(frozen=True)
class LedgerEntry:
    id: int
    delta: int
    reason: str
    balance_after: int
    ref_job_id: str | None
    note: str
    created_at: datetime


class CreditService:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    # -- internal -------------------------------------------------------------

    def _apply(self, owner_id: str, delta: int, reason: str, *, ref_job_id: str | None = None,
               ref_order_id: str | None = None, note: str = "") -> int:
        if reason not in REASONS:
            raise ValueError(f"unknown ledger reason {reason!r}")
        with self.session_factory() as s:
            dialect = s.get_bind().dialect.name
            stmt = select(User).where(User.id == owner_id)
            if dialect == "postgresql":
                stmt = stmt.with_for_update()
            user = s.scalars(stmt).first()
            if user is None:
                raise LookupError(f"unknown user {owner_id!r}")
            new_balance = user.credits_balance + delta
            if new_balance < 0:
                raise InsufficientCredits(
                    f"balance {user.credits_balance} is not enough for {-delta} credit(s)"
                )
            user.credits_balance = new_balance
            s.add(CreditLedger(
                owner_id=owner_id, delta=delta, reason=reason, ref_job_id=ref_job_id,
                ref_order_id=ref_order_id, balance_after=new_balance, note=note[:300],
                created_at=utcnow(),
            ))
            s.commit()
            return new_balance

    # -- public ---------------------------------------------------------------

    def balance(self, owner_id: str) -> int:
        with self.session_factory() as s:
            user = s.get(User, owner_id)
            return 0 if user is None else int(user.credits_balance)

    def grant(self, owner_id: str, credits: int, reason: str = "adjust_admin", note: str = "") -> int:
        if credits <= 0:
            raise ValueError("grant needs a positive number of credits")
        return self._apply(owner_id, credits, reason, note=note)

    def charge(self, owner_id: str, job_id: str, credits: int = 1) -> int:
        """Reserve credits for a job; raises InsufficientCredits when short."""
        if credits <= 0:
            raise ValueError("charge needs a positive number of credits")
        return self._apply(owner_id, -credits, "extraction", ref_job_id=job_id)

    def refund(self, owner_id: str, job_id: str, credits: int = 1, note: str = "") -> int:
        if credits <= 0:
            raise ValueError("refund needs a positive number of credits")
        return self._apply(owner_id, credits, "refund", ref_job_id=job_id, note=note)

    def history(self, owner_id: str, limit: int = 100) -> list[LedgerEntry]:
        stmt = (select(CreditLedger).where(CreditLedger.owner_id == owner_id)
                .order_by(CreditLedger.id.desc()).limit(limit))
        with self.session_factory() as s:
            rows = s.scalars(stmt).all()
        return [LedgerEntry(r.id, r.delta, r.reason, r.balance_after, r.ref_job_id, r.note, r.created_at)
                for r in rows]
