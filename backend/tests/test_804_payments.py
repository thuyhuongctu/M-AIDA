"""8.0: credit-pack purchases (payments.py) - payOS signatures, the mock
checkout, the payOS webhook and status check, and exactly-once crediting.

The reference signatures below were produced with payOS's official Python
SDK (payos 1.1.0, CryptoProvider) on the same inputs, so they pin our
implementation to the provider's.
"""

from __future__ import annotations

import importlib
import json
from datetime import timedelta

import httpx
import pytest
from conftest import fresh_database_url
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

CHECKSUM = "test-checksum-key"

# ----------------------------------------------------------------------------- signatures


def test_request_signature_matches_the_official_sdk():
    from payments import payos_request_signature

    sig = payos_request_signature(
        amount=149000, cancel_url="https://maida.test/?payment=cancel&order=123456789012",
        description="MA6789012", order_code=123456789012,
        return_url="https://maida.test/?payment=return&order=123456789012", checksum_key=CHECKSUM)
    assert sig == "f6d5d86449f93e269e7b138dd53352487e0f2b041ad73c2c472fc9678d8f9810"


SAMPLE_WEBHOOK_DATA = {
    "orderCode": 123, "amount": 3000, "description": "VQRIO123", "accountNumber": "12345678",
    "reference": "TF230204212323", "transactionDateTime": "2023-02-04 18:25:00", "currency": "VND",
    "paymentLinkId": "124c33293c43417ab7879e14c8d9eb18", "code": "00", "desc": "Thành công",
    "counterAccountBankId": "", "counterAccountBankName": "", "counterAccountName": None,
    "counterAccountNumber": None, "virtualAccountName": "", "virtualAccountNumber": "",
}


def test_data_signature_matches_the_official_sdk():
    from payments import payos_data_signature, signature_matches

    sig = payos_data_signature(SAMPLE_WEBHOOK_DATA, CHECKSUM)
    assert sig == "15cd38e52473536ad13caec70a9d5fd6446d63812d84e3ab2af193feb5dded64"
    assert signature_matches(SAMPLE_WEBHOOK_DATA, sig, CHECKSUM)
    tampered = dict(SAMPLE_WEBHOOK_DATA, amount=300000)
    assert not signature_matches(tampered, sig, CHECKSUM)
    assert not signature_matches(SAMPLE_WEBHOOK_DATA, sig, "another-key")


# ----------------------------------------------------------------------------- fixtures


def _app(tmp_path, monkeypatch, **env):
    monkeypatch.setenv("MAIDA_AUTH_MODE", env.pop("MAIDA_AUTH_MODE", "mock"))
    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "pay.db"))
    url = fresh_database_url(tmp_path, "pay")
    if not url.startswith("sqlite"):
        monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MAIDA_ADMIN_EMAILS", "operator@example.org")
    monkeypatch.setenv("MAIDA_INVITED_EMAILS", "@example.org")
    monkeypatch.setenv("MAIDA_BETA_CREDITS", "3")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.delenv("MAIDA_DEMO_MODE", raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    import settings as settings_module

    settings_module._settings = None
    main = importlib.import_module("main")
    importlib.reload(main)
    client = TestClient(main.app)

    def login(email):
        r = client.post("/api/auth/mock-login", json={"email": email})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return main, client, login


@pytest.fixture()
def mockpay(tmp_path, monkeypatch):
    import settings as settings_module

    main, client, login = _app(tmp_path, monkeypatch, MAIDA_PAYMENTS="mock")
    yield main, client, login
    monkeypatch.undo()
    settings_module._settings = None
    importlib.reload(main)


class FakePayOS:
    """httpx transport answering like payOS's merchant API."""

    def __init__(self):
        self.created: list[dict] = []
        self.status: dict[int, dict] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        from payments import payos_data_signature

        assert request.headers["x-client-id"] == "cid" and request.headers["x-api-key"] == "akey"
        if request.method == "POST" and request.url.path == "/v2/payment-requests":
            body = json.loads(request.content)
            self.created.append(body)
            data = {"paymentLinkId": f"link{body['orderCode']}", "orderCode": body["orderCode"],
                    "amount": body["amount"], "status": "PENDING",
                    "checkoutUrl": f"https://pay.payos.vn/web/link{body['orderCode']}"}
            return httpx.Response(200, json={"code": "00", "desc": "success", "data": data,
                                             "signature": payos_data_signature(data, CHECKSUM)})
        if request.method == "GET" and request.url.path.startswith("/v2/payment-requests/"):
            code = int(request.url.path.rsplit("/", 1)[1])
            data = self.status.get(code, {"status": "PENDING", "amountPaid": 0, "transactions": []})
            return httpx.Response(200, json={"code": "00", "desc": "success", "data": data})
        return httpx.Response(404, json={"code": "99", "desc": "not found"})


@pytest.fixture()
def payos(tmp_path, monkeypatch):
    import settings as settings_module

    main, client, login = _app(
        tmp_path, monkeypatch, MAIDA_PAYMENTS="payos", PAYOS_CLIENT_ID="cid", PAYOS_API_KEY="akey",
        PAYOS_CHECKSUM_KEY=CHECKSUM, MAIDA_PUBLIC_URL="https://maida.test")
    fake = FakePayOS()
    main._payments.provider._http = httpx.Client(
        base_url="https://api-merchant.payos.vn", transport=httpx.MockTransport(fake),
        headers={"x-client-id": "cid", "x-api-key": "akey"})
    yield main, client, login, fake
    monkeypatch.undo()
    settings_module._settings = None
    importlib.reload(main)


def _signed(data: dict) -> dict:
    from payments import payos_data_signature

    return {"code": "00", "desc": "success", "success": True, "data": data,
            "signature": payos_data_signature(data, CHECKSUM)}


def _paid_data(order: dict, **over) -> dict:
    data = dict(SAMPLE_WEBHOOK_DATA, orderCode=order["order_code"], amount=order["amount"],
                description=f"MA{order['order_code'] % 10**7:07d}", reference="FT26277123456",
                paymentLinkId=f"link{order['order_code']}")
    data.update(over)
    return data


def _credits(client, headers) -> int:
    return client.get("/api/me", headers=headers).json()["credits"]


# ----------------------------------------------------------------------------- mock checkout


def test_mock_purchase_credits_exactly_once(mockpay):
    _main, client, login = mockpay
    alice = login("alice@example.org")
    assert client.get("/api/config").json()["payments"] == "mock"
    packs = client.get("/api/payments/packs", headers=alice).json()
    assert packs["enabled"] and [p["id"] for p in packs["packs"]] == ["thu", "tongquan", "nhom"]
    assert packs["packs"][1] == {"id": "tongquan", "credits": 100, "price_vnd": 399000}

    r = client.post("/api/payments/orders", headers=alice, json={"pack_id": "tongquan"})
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "pending" and order["credits"] == 100 and order["amount"] == 399000
    assert order["currency"] == "VND" and len(str(order["order_code"])) == 12
    assert order["checkout_url"] == f"/api/payments/mock/checkout/{order['order_code']}"

    page = client.get(order["checkout_url"])
    assert page.status_code == 200 and "399.000" in page.text
    paid = client.post(f"{order['checkout_url']}/pay", follow_redirects=False)
    assert paid.status_code == 303 and paid.headers["location"] == f"/?payment=return&order={order['order_code']}"
    assert _credits(client, alice) == 3 + 100

    # Paying again (or a late duplicate notification) adds nothing.
    client.post(f"{order['checkout_url']}/pay", follow_redirects=False)
    assert _credits(client, alice) == 103
    synced = client.post(f"/api/payments/orders/{order['order_code']}/sync", headers=alice).json()
    assert synced["status"] == "paid" and synced["checkout_url"] == "" and synced["paid_at"]
    ledger = client.get("/api/me/ledger", headers=alice).json()
    assert [(e["reason"], e["delta"]) for e in ledger] == [("purchase", 100), ("grant_beta", 3)]


def test_orders_are_private_to_their_owner(mockpay):
    _main, client, login = mockpay
    alice, bob = login("alice@example.org"), login("bob@example.org")
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    assert client.get("/api/payments/orders", headers=bob).json() == []
    assert client.post(f"/api/payments/orders/{order['id']}/sync", headers=bob).status_code == 404
    assert client.post(f"/api/payments/orders/{order['order_code']}/cancel", headers=bob).status_code == 404
    assert [o["id"] for o in client.get("/api/payments/orders", headers=alice).json()] == [order["id"]]


def test_cancel_unknown_pack_and_rate_limit(mockpay):
    _main, client, login = mockpay
    alice = login("alice@example.org")
    assert client.post("/api/payments/orders", headers=alice, json={"pack_id": "gold"}).status_code == 404
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    back = client.post(f"/api/payments/orders/{order['order_code']}/cancel", headers=alice).json()
    assert back["status"] == "cancelled" and back["checkout_url"] == ""
    # Money arriving for a cancelled order is still credited: the user paid.
    client.post(f"/api/payments/mock/checkout/{order['order_code']}/pay", follow_redirects=False)
    assert _credits(client, alice) == 3 + 30
    for _ in range(5):  # 6 orders in the hour, the 7th is refused
        assert client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).status_code == 201
    r = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"})
    assert r.status_code == 429


def test_admin_sees_all_orders_and_paid_totals(mockpay):
    _main, client, login = mockpay
    alice, op = login("alice@example.org"), login("operator@example.org")
    o1 = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    client.post("/api/payments/orders", headers=alice, json={"pack_id": "nhom"})
    client.post(f"/api/payments/mock/checkout/{o1['order_code']}/pay", follow_redirects=False)
    assert client.get("/api/admin/orders", headers=alice).status_code == 403
    report = client.get("/api/admin/orders", headers=op).json()
    assert report["paid_orders"] == 1 and report["paid_amount_vnd"] == 149000 and report["paid_credits"] == 30
    assert {o["email"] for o in report["orders"]} == {"alice@example.org"} and len(report["orders"]) == 2


def test_ledger_refuses_a_second_purchase_credit_for_one_order(mockpay):
    main, client, login = mockpay
    alice = login("alice@example.org")
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    from db import CreditLedger, utcnow

    with main._sessions() as s:
        uid = client.get("/api/me", headers=alice).json()["id"]
        s.add(CreditLedger(owner_id=uid, delta=30, reason="purchase", ref_order_id=order["id"],
                           balance_after=33, note="", created_at=utcnow()))
        s.commit()
        s.add(CreditLedger(owner_id=uid, delta=30, reason="purchase", ref_order_id=order["id"],
                           balance_after=63, note="", created_at=utcnow()))
        with pytest.raises(IntegrityError):
            s.commit()


# ----------------------------------------------------------------------------- payOS


def test_payos_link_webhook_and_replay(payos):
    _main, client, login, fake = payos
    alice = login("alice@example.org")
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    sent = fake.created[-1]
    code = order["order_code"]
    assert sent["amount"] == 149000 and sent["orderCode"] == code
    assert sent["description"] == f"MA{code % 10**7:07d}" and len(sent["description"]) <= 9
    assert sent["returnUrl"] == f"https://maida.test/?payment=return&order={code}"
    assert sent["cancelUrl"] == f"https://maida.test/?payment=cancel&order={code}"
    from payments import payos_request_signature

    assert sent["signature"] == payos_request_signature(
        amount=149000, cancel_url=sent["cancelUrl"], description=sent["description"],
        order_code=code, return_url=sent["returnUrl"], checksum_key=CHECKSUM)
    assert order["checkout_url"] == f"https://pay.payos.vn/web/link{code}"

    hook = _signed(_paid_data(order))
    r = client.post("/api/payments/payos/webhook", json=hook)
    assert r.status_code == 200 and r.json() == {"success": True, "result": "credited"}
    assert _credits(client, alice) == 33
    # payOS retries: no second credit.
    assert client.post("/api/payments/payos/webhook", json=hook).json()["result"] == "ok"
    assert _credits(client, alice) == 33
    mine = client.get("/api/payments/orders", headers=alice).json()[0]
    assert mine["status"] == "paid" and mine["payment_reference"] == "FT26277123456"


def test_payos_webhook_rejects_forgeries_and_ignores_the_rest(payos):
    _main, client, login, _fake = payos
    alice = login("alice@example.org")
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "nhom"}).json()

    forged = _signed(_paid_data(order))
    forged["data"]["amount"] = 990000 * 10  # tampered after signing
    assert client.post("/api/payments/payos/webhook", json=forged).status_code == 400
    assert client.post("/api/payments/payos/webhook", json={"data": {}}).status_code == 400
    assert client.post("/api/payments/payos/webhook", content=b"not json",
                       headers={"Content-Type": "application/json"}).status_code == 400

    # payOS's own test call when the webhook URL is registered (unknown order).
    test_call = client.post("/api/payments/payos/webhook", json=_signed(dict(SAMPLE_WEBHOOK_DATA)))
    assert test_call.status_code == 200 and test_call.json()["success"] is True

    # A failed payment notification and an underpayment add nothing.
    assert client.post("/api/payments/payos/webhook",
                       json=_signed(_paid_data(order, code="01", desc="fail"))).json()["result"] == "ignored"
    client.post("/api/payments/payos/webhook", json=_signed(_paid_data(order, amount=100000)))
    assert _credits(client, alice) == 3
    pending = client.get("/api/payments/orders", headers=alice).json()[0]
    assert pending["status"] == "pending" and pending["payment_reference"].startswith("UNDERPAID 100000")


def test_payos_status_check_credits_when_the_webhook_is_missing(payos):
    _main, client, login, fake = payos
    alice = login("alice@example.org")
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "tongquan"}).json()
    code = order["order_code"]
    assert client.post(f"/api/payments/orders/{code}/sync", headers=alice).json()["status"] == "pending"
    fake.status[code] = {"status": "PAID", "amountPaid": 399000,
                         "transactions": [{"reference": "FT9999", "amount": 399000}]}
    synced = client.post(f"/api/payments/orders/{code}/sync", headers=alice).json()
    assert synced["status"] == "paid" and synced["payment_reference"] == "FT9999"
    assert _credits(client, alice) == 103
    # The webhook arriving afterwards changes nothing.
    client.post("/api/payments/payos/webhook", json=_signed(_paid_data(order)))
    assert _credits(client, alice) == 103

    other = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    fake.status[other["order_code"]] = {"status": "CANCELLED", "amountPaid": 0}
    assert client.post(f"/api/payments/orders/{other['id']}/sync", headers=alice).json()["status"] == "cancelled"


def test_payos_provider_error_marks_the_order_failed(payos):
    main, client, login, _fake = payos

    def refuse(request):
        return httpx.Response(200, json={"code": "20", "desc": "Thông tin truyền lên không đúng"})

    main._payments.provider._http = httpx.Client(base_url="https://api-merchant.payos.vn",
                                                 transport=httpx.MockTransport(refuse))
    alice = login("alice@example.org")
    r = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"})
    assert r.status_code == 502 and "Thông tin truyền lên không đúng" in r.json()["detail"]
    from db import Order

    with main._sessions() as s:
        assert [o.status for o in s.scalars(select(Order)).all()] == ["failed"]


# ----------------------------------------------------------------------------- configuration


class _S:
    """Stand-in for Settings in build_payment_service tests."""

    def __init__(self, **kw):
        self.payments_provider = kw.get("provider", "")
        self.maida_auth_mode = kw.get("auth", "supabase")
        self.cloud_mode = self.maida_auth_mode in ("supabase", "mock")
        self.payos_client_id = kw.get("cid", "")
        self.payos_api_key = kw.get("key", "")
        self.payos_checksum_key = kw.get("ck", "")
        self.payos_api_base = "https://api-merchant.payos.vn"
        self.maida_public_url = kw.get("url", "")
        self.maida_order_ttl_minutes = 30
        self.credit_packs = kw.get("packs", (("thu", 30, 149000),))


def test_payment_configuration_is_refused_when_unsafe_or_incomplete():
    from payments import build_payment_service

    off = build_payment_service(_S(), None)
    assert not off.enabled and off.problem == ""
    mock_real = build_payment_service(_S(provider="mock", auth="supabase"), None)
    assert not mock_real.enabled and "tests only" in mock_real.problem
    single = build_payment_service(_S(provider="payos", auth="admin_key"), None)
    assert not single.enabled and "per-user accounts" in single.problem
    missing = build_payment_service(_S(provider="payos", cid="c", key="k"), None)
    assert not missing.enabled and "PAYOS_CHECKSUM_KEY" in missing.problem and "MAIDA_PUBLIC_URL" in missing.problem
    http = build_payment_service(_S(provider="payos", cid="c", key="k", ck="x", url="http://maida.test"), None)
    assert not http.enabled and "https://" in http.problem
    ok = build_payment_service(_S(provider="payos", cid="c", key="k", ck="x", url="https://maida.test"), None)
    assert ok.enabled and ok.provider.name == "payos"


def test_credit_pack_parsing():
    from settings import Settings

    assert Settings(maida_credit_packs="a:10:50000, b:20:90000").credit_packs == (
        ("a", 10, 50000), ("b", 20, 90000))
    for bad in ("a:10", "a:0:100", "a:10:100,a:20:200", ":5:5"):
        with pytest.raises(ValueError):
            _ = Settings(maida_credit_packs=bad).credit_packs


def test_payments_are_off_by_default(tmp_path, monkeypatch):
    import settings as settings_module

    monkeypatch.delenv("MAIDA_PAYMENTS", raising=False)
    main, client, login = _app(tmp_path, monkeypatch)
    try:
        alice = login("alice@example.org")
        assert client.get("/api/config").json()["payments"] == ""
        assert client.get("/api/payments/packs", headers=alice).json() == {
            "enabled": False, "provider": "", "currency": "VND", "packs": []}
        assert client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).status_code == 503
        assert client.post("/api/payments/payos/webhook", json={}).status_code == 404
        assert client.get("/api/payments/mock/checkout/123").status_code == 404
    finally:
        monkeypatch.undo()
        settings_module._settings = None
        importlib.reload(main)


def test_expired_link_is_marked_expired_after_an_hour(mockpay):
    main, client, login = mockpay
    alice = login("alice@example.org")
    order = client.post("/api/payments/orders", headers=alice, json={"pack_id": "thu"}).json()
    from db import Order, utcnow

    with main._sessions() as s:
        row = s.get(Order, order["id"])
        row.expires_at = utcnow() - timedelta(hours=2)
        s.commit()
    assert client.post(f"/api/payments/orders/{order['id']}/sync", headers=alice).json()["status"] == "expired"
