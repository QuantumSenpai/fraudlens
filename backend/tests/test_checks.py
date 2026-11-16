from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
from schemas import CheckInput
from services import check_service
from services.check_service import create_check
from services.auth import require_merchant


def test_check_replay_returns_stored_decision_without_duplicate_or_rescore(monkeypatch):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    class Query:
        def __init__(self, database, table):
            self.database = database
            self.table = table
            self.columns = ""
            self.operation = "select"
            self.filters = {}
            self.payload = None

        def select(self, columns, **_kwargs):
            self.columns = columns
            return self

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args):
            return self

        def gte(self, *_args):
            return self

        def lte(self, *_args):
            return self

        def insert(self, payload):
            self.operation = "insert"
            self.payload = payload
            self.database.insert_count += 1
            self.database.row = {
                **payload,
                "id": "check-1",
                "created_at": now.isoformat(),
            }
            return self

        def single(self):
            return self

        def execute(self):
            if self.operation == "insert":
                return SimpleNamespace(data=[self.database.row])
            if self.table == "checks" and self.columns == "*":
                row = self.database.row
                matches = row and all(row.get(key) == value for key, value in self.filters.items())
                return SimpleNamespace(data=[row] if matches else [])
            if self.table == "devices":
                return SimpleNamespace(data=[{
                    "device_id": "device-1",
                    "first_seen": now.isoformat(),
                    "trust_score": 50,
                    "timezone": "Asia/Kolkata",
                }])
            if self.table == "device_users":
                return SimpleNamespace(count=1, data=[{"user_id": "user-1"}])
            return SimpleNamespace(data=[])

    class Database:
        insert_count = 0
        row = None

        def table(self, name):
            return Query(self, name)

        def rpc(self, name, params):
            assert name == "check_context"
            assert params["p_user_id"] == "user-1"
            return SimpleNamespace(execute=lambda: SimpleNamespace(data={
                "device": {"device_id": "device-1", "first_seen": now.isoformat(), "timezone": "Asia/Kolkata"},
                "user_checks": [],
                "legacy_transactions": [],
                "device_user_count": 1,
                "device_decisions": [],
                "failed_payment_count": 0,
            }))

    database = Database()
    model_calls = []
    monkeypatch.setattr(check_service, "datetime", FixedDateTime)
    monkeypatch.setattr(check_service, "get_supabase", lambda: database)
    monkeypatch.setattr(
        check_service.model_service,
        "predict_with_factors",
        lambda amount, tx_time, live_features: model_calls.append((amount, tx_time, live_features)) or (0.1, []),
    )
    payload = CheckInput(
        user_id="user-1",
        device_id="device-1",
        amount=50001,
        payment_method="upi",
    )

    first = create_check(payload, "merchant-1", "intent-1", "203.0.113.8")
    replay = create_check(payload.model_copy(update={"amount": 5}), "merchant-1", "intent-1", "203.0.113.8")

    assert first.check_id == replay.check_id == "check-1"
    assert first.decision == replay.decision
    assert any(reason.rule == "NEW_USER_HIGH_VALUE" for reason in first.reasons)
    assert database.insert_count == 1
    assert len(model_calls) == 1


def test_v1_checks_returns_the_frontend_contract(monkeypatch):
    from routes import checks

    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}
    monkeypatch.setattr(
        checks,
        "create_check",
        lambda payload, merchant_id, idempotency_key, client_ip: {
            "check_id": "check-1",
            "decision": "REVIEW",
            "final_score": 35,
            "ml_score": 10,
            "rule_score": 72,
            "reasons": [{"rule": "STRUCTURING", "detail": "burst", "weight": 35}],
            "model_version": "xgb_creditcard_v1",
            "ml_factors": [],
            "latency_ms": 8,
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/checks",
                headers={"X-API-Key": "fl_demo_key_with_enough_length", "Idempotency-Key": "intent-1"},
                json={
                    "user_id": "user-1",
                    "device_id": "device-1",
                    "amount": 95000,
                    "currency": "INR",
                    "payment_method": "upi",
                },
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 200
    assert response.json()["decision"] == "REVIEW"
    assert response.json()["reasons"][0]["rule"] == "STRUCTURING"


def test_v1_checks_rejects_missing_idempotency_key():
    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/checks",
                headers={"X-API-Key": "fl_demo_key_with_enough_length"},
                json={
                    "user_id": "user-1",
                    "device_id": "device-1",
                    "amount": 100,
                    "payment_method": "card",
                },
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "request_failed"


def test_legacy_predict_response_shape_remains_compatible(monkeypatch):
    from routes import predict

    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}
    monkeypatch.setattr(predict.model_service, "predict_with_factors", lambda amount, tx_time, live_features: (0.1, []))
    monkeypatch.setattr(predict, "get_user_history", lambda user_id: [])
    monkeypatch.setattr(predict, "insert_transaction", lambda *args: None)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/predict",
                headers={"X-API-Key": "fl_demo_key_with_enough_length"},
                json={
                    "user_id": "user-1",
                    "device_id": "device-1",
                    "amount": 100,
                    "time": 3600,
                    "lat": 12.97,
                    "lon": 77.59,
                    "timestamp": "2026-11-16T12:00:00",
                },
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 200
    assert set(response.json()) == {"ml_score", "rule_score", "final_score", "flagged", "triggered_rules", "model_version", "ml_factors"}
    assert response.json()["triggered_rules"][0]["rule"] == "NEW_DEVICE"
