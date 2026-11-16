import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from main import app
from services import payment_service
from services.auth import require_merchant
from services.config import Settings
from services.payment_service import checkout_signature, validate_payment_settings, webhook_signature


def test_checkout_signature_uses_server_order_id_and_constant_time_comparable_digest():
    signature = checkout_signature("order_test_1", "pay_test_1", "secret")

    assert signature == hmac.new(b"secret", b"order_test_1|pay_test_1", hashlib.sha256).hexdigest()


def test_webhook_signature_uses_exact_raw_body_bytes():
    raw = b'{ "event" : "payment.captured" }'

    assert webhook_signature(raw, "secret") == hmac.new(b"secret", raw, hashlib.sha256).hexdigest()


def test_payment_key_mode_requires_test_prefix_outside_explicit_prod():
    with pytest.raises(ValueError):
        validate_payment_settings(Settings(razorpay_key_id="rzp_live_demo", razorpay_key_secret="secret", env="dev"))

    validate_payment_settings(Settings(razorpay_key_id="rzp_test_demo", razorpay_key_secret="secret", env="dev"))
    validate_payment_settings(Settings(razorpay_key_id="rzp_live_demo", razorpay_key_secret="secret", env="prod"))


def test_webhook_endpoint_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(payment_service.settings, "razorpay_webhook_secret", "test-secret")
    with TestClient(app) as client:
        response = client.post(
            "/v1/webhooks/razorpay",
            content=b'{"event":"payment.captured"}',
            headers={"X-Razorpay-Signature": "0" * 64},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_payment_order_requires_decision_and_returns_public_key_only(monkeypatch):
    from routes import payments

    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}
    monkeypatch.setattr(payments, "create_payment_order", lambda check_id, idem, merchant_id: {
        "order_id": "order_test_1", "amount": 10000, "currency": "INR", "key_id": "rzp_test_public"
    })
    monkeypatch.setattr(payments, "validate_payment_settings", lambda *_args: None)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/payments/order",
                headers={"X-API-Key": "fl_demo_key_with_enough_length", "Idempotency-Key": "intent-order-1"},
                json={"check_id": "00000000-0000-0000-0000-000000000001"},
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 200
    assert response.json() == {
        "order_id": "order_test_1", "amount": 10000, "currency": "INR", "key_id": "rzp_test_public"
    }


def test_payment_order_refuses_live_key_outside_explicit_prod(monkeypatch):
    from routes import payments

    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}
    monkeypatch.setattr(payments.settings, "razorpay_key_id", "rzp_live_demo")
    monkeypatch.setattr(payments.settings, "razorpay_key_secret", "not-printed")
    monkeypatch.setattr(payments.settings, "env", "dev")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/payments/order",
                headers={"X-API-Key": "fl_demo_key_with_enough_length", "Idempotency-Key": "intent-order-live"},
                json={"check_id": "00000000-0000-0000-0000-000000000001"},
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Service unavailable"


@pytest.mark.parametrize(("amount", "decision", "paise"), [("125.50", "ALLOW", 12550), ("500000", "REVIEW", 50000000)])
def test_payment_order_uses_paise_stores_order_and_replays_idempotently(monkeypatch, amount, decision, paise):
    check = {
        "id": "00000000-0000-0000-0000-000000000001",
        "merchant_id": "merchant-1",
        "decision": decision,
        "amount": amount,
        "currency": "INR",
    }
    stored_payments = []
    remote_calls = []

    class Query:
        def __init__(self, table):
            self.table = table
            self.filters = {}
            self.operation = "select"
            self.payload = None

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def limit(self, *_args):
            return self

        def insert(self, payload):
            self.operation = "insert"
            self.payload = payload
            return self

        def execute(self):
            if self.operation == "insert":
                stored_payments.append(self.payload)
                return SimpleNamespace(data=[self.payload])
            rows = {
                "checks": [check],
                "payments": stored_payments,
                "reviews": [{"check_id": check["id"], "outcome": "approve"}],
            }.get(self.table, [])
            rows = [row for row in rows if all(row.get(key) == value for key, value in self.filters.items())]
            return SimpleNamespace(data=rows)

    class Database:
        def table(self, name):
            return Query(name)

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "order_test_1"}

    def fake_post(url, **kwargs):
        remote_calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(payment_service, "get_supabase", lambda: Database())
    monkeypatch.setattr(payment_service.httpx, "post", fake_post)
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_test_public")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "secret")
    monkeypatch.setattr(payment_service.settings, "env", "dev")

    first = payment_service.create_payment_order(check["id"], "order-intent-1", "merchant-1")
    replay = payment_service.create_payment_order(check["id"], "order-intent-1", "merchant-1")

    assert first == replay == {"order_id": "order_test_1", "amount": paise, "currency": "INR", "key_id": "rzp_test_public"}
    assert remote_calls[0][1]["json"] == {"amount": paise, "currency": "INR", "receipt": check["id"]}
    assert len(remote_calls) == len(stored_payments) == 1


def test_blocked_unapproved_and_legacy_high_amount_checks_cannot_create_order(monkeypatch):
    check = {"id": "check-1", "merchant_id": "merchant-1", "decision": "BLOCK", "amount": "200", "currency": "INR"}

    class Query:
        def __init__(self, table):
            self.table = table
            self.filters = {}

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def limit(self, *_args):
            return self

        def execute(self):
            row = check if self.table == "checks" else None
            return SimpleNamespace(data=[row] if row and all(row.get(k) == v for k, v in self.filters.items()) else [])

    class Database:
        def table(self, name):
            return Query(name)

    monkeypatch.setattr(payment_service, "get_supabase", lambda: Database())
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_test_public")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "secret")
    monkeypatch.setattr(payment_service.settings, "env", "dev")
    remote = []
    monkeypatch.setattr(payment_service, "_create_remote_order", lambda *args: remote.append(args) or {"id": "unexpected-order"})

    with pytest.raises(Exception) as blocked:
        payment_service.create_payment_order("check-1", "intent", "merchant-1")
    assert getattr(blocked.value, "status_code", None) == 409

    check["decision"] = "REVIEW"
    with pytest.raises(Exception) as pending:
        payment_service.create_payment_order("check-1", "intent", "merchant-1")
    assert getattr(pending.value, "status_code", None) == 409

    check.update(decision="ALLOW", amount="500000")
    with pytest.raises(Exception) as legacy:
        payment_service.create_payment_order("check-1", "intent", "merchant-1")
    assert getattr(legacy.value, "status_code", None) == 409
    assert remote == []


def test_verify_checkout_payment_uses_stored_order_and_updates_authorized_status(monkeypatch):
    payment = {"id": "payment-row", "check_id": "check-row", "razorpay_order_id": "order_test_1", "status": "created"}
    updates = []

    class Query:
        def __init__(self, table):
            self.table = table
            self.filters = {}
            self.operation = "select"

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def limit(self, *_args):
            return self

        def update(self, values):
            self.operation = "update"
            updates.append((self.table, values))
            return self

        def execute(self):
            if self.operation == "update":
                return SimpleNamespace(data=[])
            row = payment if self.table == "payments" else {"id": "check-row", "merchant_id": "merchant-1"}
            return SimpleNamespace(data=[row] if all(row.get(k) == v for k, v in self.filters.items()) else [])

    class Database:
        def table(self, name):
            return Query(name)

    monkeypatch.setattr(payment_service, "get_supabase", lambda: Database())
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_test_public")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "secret")
    monkeypatch.setattr(payment_service.settings, "env", "dev")
    signature = checkout_signature("order_test_1", "pay_test_1", "secret")

    result = payment_service.verify_checkout_payment("order_test_1", "pay_test_1", signature, "merchant-1")

    assert result == {"order_id": "order_test_1", "payment_id": "pay_test_1", "status": "authorized"}
    assert updates[0][1]["status"] == "authorized"


def test_webhook_processing_is_idempotent_and_does_not_downgrade_captured_payment(monkeypatch):
    payment = {"id": "payment-row", "status": "captured"}
    event_ids = set()
    updates = []

    class Query:
        def __init__(self, table):
            self.table = table
            self.filters = {}
            self.operation = "select"
            self.payload = None

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def limit(self, *_args):
            return self

        def update(self, values):
            self.operation = "update"
            self.payload = values
            return self

        def insert(self, payload):
            self.operation = "insert"
            self.payload = payload
            return self

        def execute(self):
            if self.table == "payments":
                if self.operation == "update":
                    updates.append(self.payload)
                    return SimpleNamespace(data=[])
                return SimpleNamespace(data=[payment] if self.filters.get("razorpay_order_id") == "order_test_1" else [])
            if self.operation == "insert":
                event_ids.add(self.payload["event_id"])
                return SimpleNamespace(data=[self.payload])
            return SimpleNamespace(data=[{"event_id": value} for value in event_ids if value == self.filters.get("event_id")])

    class Database:
        def table(self, name):
            return Query(name)

    monkeypatch.setattr(payment_service, "get_supabase", lambda: Database())
    raw = b'{"event":"payment.failed"}'
    event = {"event": "payment.failed", "payload": {"payment": {"entity": {"order_id": "order_test_1", "id": "pay_test_1"}}}}

    first = payment_service.process_webhook(event, "evt-test-1", raw)
    replay = payment_service.process_webhook(event, "evt-test-1", raw)

    assert first == {"received": True, "duplicate": False}
    assert replay == {"received": True, "duplicate": True}
    assert len(updates) == 1
    assert "status" not in updates[0]
    assert "razorpay_payment_id" not in updates[0]


def test_valid_webhook_signature_is_checked_before_event_processing(monkeypatch):
    from routes import payments

    raw = b'{"event":"payment.captured"}'
    called = []
    monkeypatch.setattr(payments.settings, "razorpay_webhook_secret", "secret")
    monkeypatch.setattr(payments, "process_webhook", lambda event, event_id, body: called.append((event, event_id, body)) or {"received": True, "duplicate": False})
    signature = webhook_signature(raw, "secret")

    with TestClient(app) as client:
        response = client.post(
            "/v1/webhooks/razorpay",
            content=raw,
            headers={"X-Razorpay-Signature": signature, "x-razorpay-event-id": "evt-test-2"},
        )

    assert response.status_code == 200
    assert called == [({"event": "payment.captured"}, "evt-test-2", raw)]
