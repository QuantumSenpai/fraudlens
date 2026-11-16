from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
from services.auth import require_merchant
from services.config import settings
from services import payment_service


def test_payment_order_endpoint_with_supabase_and_razorpay_mocks(monkeypatch):
    check_id = "00000000-0000-0000-0000-000000000401"
    check = {
        "id": check_id,
        "merchant_id": "merchant-e2e",
        "decision": "ALLOW",
        "amount": "499.50",
        "currency": "INR",
    }
    saved_payments = []
    remote_requests = []

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
                saved_payments.append(self.payload)
                return SimpleNamespace(data=[self.payload])
            rows = [check] if self.table == "checks" else saved_payments if self.table == "payments" else []
            return SimpleNamespace(data=[row for row in rows if all(row.get(k) == v for k, v in self.filters.items())])

    class Database:
        def table(self, name):
            return Query(name)

    class RazorpayResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "order_test_e2e"}

    def fake_razorpay_post(url, **kwargs):
        remote_requests.append((url, kwargs))
        return RazorpayResponse()

    monkeypatch.setattr(payment_service, "get_supabase", lambda: Database())
    monkeypatch.setattr(payment_service.httpx, "post", fake_razorpay_post)
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_public_only")
    monkeypatch.setattr(settings, "razorpay_key_secret", "server-only-secret")
    monkeypatch.setattr(settings, "env", "dev")
    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-e2e"}
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/payments/order",
                headers={"X-API-Key": "fl_demo_key_with_enough_length", "Idempotency-Key": "e2e-order-1"},
                json={"check_id": check_id},
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 200
    assert response.json() == {
        "order_id": "order_test_e2e",
        "amount": 49950,
        "currency": "INR",
        "key_id": "rzp_test_public_only",
    }
    assert "server-only-secret" not in response.text
    assert remote_requests[0][1]["json"] == {"amount": 49950, "currency": "INR", "receipt": check_id}
    assert saved_payments[0]["razorpay_order_id"] == "order_test_e2e"
