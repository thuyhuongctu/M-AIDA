"""
Credit-pack purchases for M-AIDA 8.x.

Flow (payOS, VietQR bank transfer)
----------------------------------
1. The signed-in user picks a pack; ``create_order`` writes a *pending* order
   (so a fast notification always finds it) and asks payOS for a payment link.
2. The browser goes to payOS's checkout page; the user pays by bank transfer.
3. payOS POSTs a signed notification to ``/api/payments/payos/webhook``.
   ``handle_webhook`` checks the HMAC-SHA256 signature with the channel's
   checksum key and, for a successful payment, calls ``confirm_paid``.
4. payOS sends the browser back to ``MAIDA_PUBLIC_URL/?payment=return...``;
   the page calls ``sync_order``, which asks payOS for the order's status, so
   credits arrive even if the webhook is late or was never configured.

``confirm_paid`` is the only place credits are bought. It runs in one
transaction (order row and user row locked on Postgres), refuses an order
that is already paid, refuses a payment smaller than the price, and relies on
the partial unique index ``ux_ledger_purchase_order`` (migration 0003) as the
last line of defence: one order can add credits once, whatever races.

Money that arrives for an order the site had marked cancelled or expired is
still credited: the user paid. Underpaid orders are left pending for the
operator to settle by hand (they appear in the admin order list).

Signatures follow the payOS documentation and its official SDKs:
* payment request: HMAC_SHA256(checksum_key,
  "amount=..&cancelUrl=..&description=..&orderCode=..&returnUrl=..");
* webhook and response data: every key of ``data`` sorted, ``key=value``
  joined by "&", null as empty string, lists as compact JSON.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db import AuditLog, CreditLedger, Order, User, utcnow

logger = logging.getLogger(__name__)

ORDER_STATUSES = ("pending", "paid", "cancelled", "expired", "failed")
#: At most this many new orders per user per hour (stops link spamming).
MAX_ORDERS_PER_HOUR = 6


@dataclass(frozen=True)
class CreditPack:
    id: str
    credits: int
    price_vnd: int


class PaymentError(Exception):
    """An error with an HTTP status the API layer can return as is."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class WebhookInvalid(Exception):
    """The notification is malformed or its signature does not match."""


# ---------------------------------------------------------------------------
# payOS signatures
# ---------------------------------------------------------------------------


def _hmac(key: str, message: str) -> str:
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _str_value(value: Any) -> str:
    if value is None or value in ("undefined", "null"):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        items = [dict(sorted(v.items())) if isinstance(v, dict) else v for v in value]
        return json.dumps(items, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def payos_request_signature(*, amount: int, cancel_url: str, description: str, order_code: int,
                            return_url: str, checksum_key: str) -> str:
    message = (f"amount={amount}&cancelUrl={cancel_url}&description={description}"
               f"&orderCode={order_code}&returnUrl={return_url}")
    return _hmac(checksum_key, message)


def payos_data_signature(data: dict[str, Any], checksum_key: str) -> str:
    message = "&".join(f"{k}={_str_value(data[k])}" for k in sorted(data))
    return _hmac(checksum_key, message)


def signature_matches(data: dict[str, Any], signature: str, checksum_key: str) -> bool:
    if not signature or not checksum_key:
        return False
    return hmac.compare_digest(payos_data_signature(data, checksum_key), str(signature))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class Provider(Protocol):
    name: str

    def create_link(self, *, order_code: int, amount: int, description: str, return_url: str,
                    cancel_url: str, expired_at: int) -> dict[str, Any]: ...

    def get_status(self, order_code: int) -> dict[str, Any]: ...

    def verify_webhook(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class PayOSProvider:
    """Minimal payOS client (create link, read status, verify notifications)."""

    name = "payos"

    def __init__(self, *, client_id: str, api_key: str, checksum_key: str,
                 base_url: str = "https://api-merchant.payos.vn",
                 transport: httpx.BaseTransport | None = None, timeout: float = 15.0) -> None:
        self.checksum_key = checksum_key
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport,
            headers={"x-client-id": client_id, "x-api-key": api_key,
                     "Content-Type": "application/json"},
        )

    def _unwrap(self, response: httpx.Response, *, check_signature: bool) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise PaymentError(502, f"payOS answered HTTP {response.status_code} without JSON") from exc
        if response.status_code >= 400 or str(body.get("code")) != "00":
            raise PaymentError(502, f"payOS refused the request: {body.get('desc') or response.status_code}")
        data = body.get("data") or {}
        if check_signature and body.get("signature") and not signature_matches(
                data, body["signature"], self.checksum_key):
            raise PaymentError(502, "payOS answer failed the signature check")
        return data

    def create_link(self, *, order_code: int, amount: int, description: str, return_url: str,
                    cancel_url: str, expired_at: int) -> dict[str, Any]:
        payload = {
            "orderCode": order_code, "amount": amount, "description": description,
            "returnUrl": return_url, "cancelUrl": cancel_url, "expiredAt": expired_at,
            "signature": payos_request_signature(
                amount=amount, cancel_url=cancel_url, description=description,
                order_code=order_code, return_url=return_url, checksum_key=self.checksum_key),
        }
        return self._unwrap(self._http.post("/v2/payment-requests", json=payload), check_signature=True)

    def get_status(self, order_code: int) -> dict[str, Any]:
        return self._unwrap(self._http.get(f"/v2/payment-requests/{order_code}"), check_signature=False)

    def verify_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if not isinstance(data, dict) or not payload.get("signature"):
            raise WebhookInvalid("missing data or signature")
        if not signature_matches(data, payload["signature"], self.checksum_key):
            raise WebhookInvalid("signature mismatch")
        return data


class MockProvider:
    """Local fake checkout (tests, e2e). Never used with real sign-in."""

    name = "mock"

    def create_link(self, *, order_code: int, amount: int, description: str, return_url: str,
                    cancel_url: str, expired_at: int) -> dict[str, Any]:
        return {"checkoutUrl": f"/api/payments/mock/checkout/{order_code}",
                "paymentLinkId": f"mock-{order_code}", "status": "PENDING"}

    def get_status(self, order_code: int) -> dict[str, Any]:
        # Payment state of the mock lives in the orders table (set by the
        # mock checkout page through PaymentService.confirm_paid).
        return {"status": "PENDING", "amountPaid": 0}

    def verify_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise WebhookInvalid("the mock provider has no webhook")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def order_to_dict(o: Order, email: str | None = None) -> dict[str, Any]:
    d = {
        "id": o.id, "order_code": o.order_code, "pack_id": o.pack_id, "credits": o.credits,
        "amount": int(o.amount), "currency": o.currency, "status": o.status,
        "provider": o.provider, "checkout_url": o.checkout_url if o.status == "pending" else "",
        "payment_reference": o.payment_reference, "created_at": o.created_at,
        "paid_at": o.paid_at, "expires_at": o.expires_at,
    }
    if email is not None:
        d["email"] = email
    return d


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class PaymentService:
    def __init__(self, session_factory: sessionmaker, *, provider: Provider | None,
                 packs: tuple[tuple[str, int, int], ...], public_url: str = "",
                 ttl_minutes: int = 30, problem: str = "") -> None:
        self.session_factory = session_factory
        self.provider = provider
        self.packs = tuple(CreditPack(*p) for p in packs)
        self.public_url = public_url.rstrip("/")
        self.ttl_minutes = ttl_minutes
        #: Why payments are off although MAIDA_PAYMENTS is set ("" = fine).
        self.problem = problem

    # -- configuration --------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.provider is not None and bool(self.packs) and not self.problem

    def pack(self, pack_id: str) -> CreditPack:
        for p in self.packs:
            if p.id == pack_id:
                return p
        raise PaymentError(404, f"Unknown credit pack {pack_id!r}.")

    def _return_urls(self, order_code: int) -> tuple[str, str]:
        base = self.public_url
        return (f"{base}/?payment=return&order={order_code}",
                f"{base}/?payment=cancel&order={order_code}")

    # -- orders ---------------------------------------------------------------

    def _new_order_code(self, s) -> int:
        for _ in range(20):
            code = 10**11 + secrets.randbelow(9 * 10**11)  # 12 digits
            if s.scalars(select(Order.id).where(Order.order_code == code)).first() is None:
                return code
        raise PaymentError(503, "Could not allocate an order code; try again.")

    def create_order(self, owner_id: str, pack_id: str) -> dict[str, Any]:
        if not self.enabled:
            raise PaymentError(503, self.problem or "Payments are not enabled on this server.")
        pack = self.pack(pack_id)
        now = utcnow()
        with self.session_factory() as s:
            recent = s.scalar(select(func.count(Order.id)).where(
                Order.owner_id == owner_id, Order.created_at >= now - timedelta(hours=1)))
            if (recent or 0) >= MAX_ORDERS_PER_HOUR:
                raise PaymentError(429, "Too many payment links in the last hour; finish or wait for the pending ones.")
            code = self._new_order_code(s)
            order = Order(
                id=uuid.uuid4().hex, owner_id=owner_id, provider=self.provider.name,
                amount=float(pack.price_vnd), currency="VND", credits=pack.credits,
                status="pending", created_at=now, order_code=code, pack_id=pack.id,
                expires_at=now + timedelta(minutes=self.ttl_minutes), updated_at=now,
            )
            s.add(order)
            s.commit()
            order_id = order.id
        return_url, cancel_url = self._return_urls(code)
        try:
            link = self.provider.create_link(
                order_code=code, amount=pack.price_vnd, description=f"MA{code % 10**7:07d}",
                return_url=return_url, cancel_url=cancel_url,
                expired_at=int((now + timedelta(minutes=self.ttl_minutes)).timestamp()),
            )
        except PaymentError as exc:
            self._set_status(order_id, "failed")
            logger.warning("payment link for order %s failed: %s", code, exc.detail)
            raise
        except httpx.HTTPError as exc:
            self._set_status(order_id, "failed")
            raise PaymentError(502, f"Could not reach the payment provider ({type(exc).__name__}).") from exc
        with self.session_factory() as s:
            order = s.get(Order, order_id)
            order.provider_order_id = str(link.get("paymentLinkId") or "")[:120]
            order.checkout_url = str(link.get("checkoutUrl") or "")[:500]
            order.updated_at = utcnow()
            s.commit()
            return order_to_dict(order)

    def _set_status(self, order_id: str, status: str) -> None:
        with self.session_factory() as s:
            order = s.get(Order, order_id)
            if order is not None and order.status != "paid":
                order.status = status
                order.updated_at = utcnow()
                s.commit()

    def list_orders(self, owner_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.session_factory() as s:
            rows = s.scalars(select(Order).where(Order.owner_id == owner_id)
                             .order_by(Order.created_at.desc()).limit(limit)).all()
            return [order_to_dict(o) for o in rows]

    def _find(self, s, owner_id: str, ref: str) -> Order | None:
        stmt = select(Order).where(Order.owner_id == owner_id)
        if ref.isdigit():
            stmt = stmt.where(Order.order_code == int(ref))
        else:
            stmt = stmt.where(Order.id == ref)
        return s.scalars(stmt).first()

    def get_order(self, owner_id: str, ref: str) -> dict[str, Any]:
        with self.session_factory() as s:
            order = self._find(s, owner_id, ref)
            if order is None:
                raise PaymentError(404, "Order not found.")
            return order_to_dict(order)

    # -- payment confirmation -------------------------------------------------

    def confirm_paid(self, order_code: int, *, amount_paid: int, reference: str, source: str) -> bool:
        """Credit a paid order once. Returns True when credits were added now."""
        with self.session_factory() as s:
            dialect = s.get_bind().dialect.name
            stmt = select(Order).where(Order.order_code == order_code)
            if dialect == "postgresql":
                stmt = stmt.with_for_update()
            order = s.scalars(stmt).first()
            if order is None:
                logger.info("payment for unknown order code %s ignored (%s)", order_code, source)
                return False
            if order.status == "paid":
                return False
            if amount_paid < int(order.amount):
                logger.warning("order %s underpaid: %s < %s (%s); left for the operator",
                               order_code, amount_paid, int(order.amount), source)
                order.payment_reference = f"UNDERPAID {amount_paid} {reference}"[:120]
                order.updated_at = utcnow()
                s.commit()
                return False
            ustmt = select(User).where(User.id == order.owner_id)
            if dialect == "postgresql":
                ustmt = ustmt.with_for_update()
            user = s.scalars(ustmt).first()
            if user is None:
                logger.error("order %s belongs to a missing user %s", order_code, order.owner_id)
                return False
            now = utcnow()
            user.credits_balance += order.credits
            s.add(CreditLedger(
                owner_id=user.id, delta=order.credits, reason="purchase", ref_order_id=order.id,
                balance_after=user.credits_balance, created_at=now,
                note=f"{order.pack_id} {int(order.amount)} {order.currency} ({order.provider} {reference})"[:300],
            ))
            order.status = "paid"
            order.paid_at = now
            order.updated_at = now
            order.payment_reference = (reference or "")[:120]
            s.add(AuditLog(owner_id=user.id, action="purchase", detail={
                "order_code": order_code, "credits": order.credits, "amount": int(order.amount),
                "currency": order.currency, "source": source}, created_at=now))
            try:
                s.commit()
            except IntegrityError:
                # Another path credited the same order a moment earlier.
                s.rollback()
                return False
            return True

    def handle_webhook(self, payload: dict[str, Any]) -> str:
        if self.provider is None:
            raise WebhookInvalid("payments are not enabled")
        data = self.provider.verify_webhook(payload)
        if str(data.get("code")) != "00" or payload.get("success") is False:
            return "ignored"
        try:
            order_code = int(data.get("orderCode"))
            amount = int(data.get("amount"))
        except (TypeError, ValueError) as exc:
            raise WebhookInvalid("orderCode/amount missing") from exc
        credited = self.confirm_paid(order_code, amount_paid=amount,
                                     reference=str(data.get("reference") or ""), source="webhook")
        return "credited" if credited else "ok"

    def sync_order(self, owner_id: str, ref: str) -> dict[str, Any]:
        """Ask the provider about one of the caller's orders and apply it."""
        with self.session_factory() as s:
            order = self._find(s, owner_id, ref)
            if order is None:
                raise PaymentError(404, "Order not found.")
            order_id, code, status, provider = order.id, order.order_code, order.status, order.provider
            expires_at = _aware(order.expires_at)
        if status == "paid" or code is None or self.provider is None or provider != self.provider.name:
            return self.get_order(owner_id, order_id)
        try:
            info = self.provider.get_status(code)
        except (PaymentError, httpx.HTTPError) as exc:
            logger.warning("status check for order %s failed: %s", code, exc)
            return self.get_order(owner_id, order_id)
        remote = str(info.get("status") or "").upper()
        if remote == "PAID":
            reference = ""
            for t in info.get("transactions") or []:
                reference = str(t.get("reference") or reference)
            self.confirm_paid(code, amount_paid=int(info.get("amountPaid") or 0),
                              reference=reference, source="status_check")
        elif remote == "CANCELLED":
            self._set_status(order_id, "cancelled")
        elif remote == "EXPIRED":
            self._set_status(order_id, "expired")
        elif remote == "PENDING" and expires_at is not None and expires_at < utcnow() - timedelta(hours=1):
            # payOS still says pending an hour after the link expired: treat
            # as expired locally; a late payment would still be credited.
            self._set_status(order_id, "expired")
        return self.get_order(owner_id, order_id)

    def mark_cancelled(self, owner_id: str, ref: str) -> dict[str, Any]:
        with self.session_factory() as s:
            order = self._find(s, owner_id, ref)
            if order is None:
                raise PaymentError(404, "Order not found.")
            order_id = order.id
        self._set_status(order_id, "cancelled")
        return self.get_order(owner_id, order_id)

    # -- operator -------------------------------------------------------------

    def admin_orders(self, limit: int = 200) -> dict[str, Any]:
        with self.session_factory() as s:
            rows = s.execute(select(Order, User.email).join(User, User.id == Order.owner_id)
                             .order_by(Order.created_at.desc()).limit(limit)).all()
            paid = s.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.amount), 0.0),
                                    func.coalesce(func.sum(Order.credits), 0))
                             .where(Order.status == "paid")).one()
        return {
            "orders": [order_to_dict(o, email) for o, email in rows],
            "paid_orders": int(paid[0]), "paid_amount_vnd": int(paid[1]), "paid_credits": int(paid[2]),
        }


def build_payment_service(settings, session_factory: sessionmaker) -> PaymentService:
    """PaymentService for the configured MAIDA_PAYMENTS (may be disabled)."""
    provider_name = settings.payments_provider
    try:
        packs = settings.credit_packs
    except ValueError as exc:
        return PaymentService(session_factory, provider=None, packs=(), problem=str(exc))
    common = {"packs": packs, "public_url": settings.maida_public_url,
              "ttl_minutes": settings.maida_order_ttl_minutes}
    if not provider_name:
        return PaymentService(session_factory, provider=None, **common)
    if not settings.cloud_mode:
        return PaymentService(session_factory, provider=None, problem=(
            "Payments need per-user accounts (MAIDA_AUTH_MODE supabase or mock)."), **common)
    if provider_name == "mock":
        if settings.maida_auth_mode != "mock":
            return PaymentService(session_factory, provider=None, problem=(
                "MAIDA_PAYMENTS=mock is for tests only and is refused with real sign-in."), **common)
        return PaymentService(session_factory, provider=MockProvider(), **common)
    if provider_name == "payos":
        missing = [n for n, v in (("PAYOS_CLIENT_ID", settings.payos_client_id),
                                  ("PAYOS_API_KEY", settings.payos_api_key),
                                  ("PAYOS_CHECKSUM_KEY", settings.payos_checksum_key),
                                  ("MAIDA_PUBLIC_URL", settings.maida_public_url)) if not v]
        if missing:
            return PaymentService(session_factory, provider=None,
                                  problem="Payments are off: missing " + ", ".join(missing) + ".", **common)
        if not settings.maida_public_url.startswith("https://"):
            return PaymentService(session_factory, provider=None, problem=(
                "MAIDA_PUBLIC_URL must start with https:// for payOS return pages."), **common)
        provider = PayOSProvider(client_id=settings.payos_client_id, api_key=settings.payos_api_key,
                                 checksum_key=settings.payos_checksum_key, base_url=settings.payos_api_base)
        return PaymentService(session_factory, provider=provider, **common)
    return PaymentService(session_factory, provider=None,
                          problem=f"Unknown MAIDA_PAYMENTS value {provider_name!r}.", **common)
