import asyncio
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from main import app, http_error
from schemas import TransactionInput
from services import auth
from services.auth import api_key_hash, require_admin, require_idempotency_key, require_merchant
from services.rate_limit import RateLimiter


def test_api_key_hash_uses_sha256():
    import hashlib

    assert api_key_hash("demo-api-key") == hashlib.sha256(b"demo-api-key").hexdigest()


def test_valid_api_key_matches_active_merchant_hash(monkeypatch):
    api_key = "fl_demo_key_with_enough_length"

    class Query:
        def select(self, *_):
            return self

        def eq(self, *_):
            return self

        def limit(self, *_):
            return self

        def execute(self):
            return SimpleNamespace(data=[{
                "id": "merchant-1",
                "api_key_hash": api_key_hash(api_key),
                "is_active": True,
            }])

    class Database:
        def table(self, *_):
            return Query()

    monkeypatch.setattr(auth, "get_supabase", Database)
    assert require_merchant(api_key)["id"] == "merchant-1"


def test_invalid_api_key_is_rejected(monkeypatch):
    class Query:
        def select(self, *_):
            return self

        def eq(self, *_):
            return self

        def limit(self, *_):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class Database:
        def table(self, *_):
            return Query()

    monkeypatch.setattr(auth, "get_supabase", Database)
    try:
        require_merchant("fl_invalid_key_with_sufficient_length")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("invalid API key was accepted")


def test_admin_bearer_token_uses_constant_time_digest_comparison(monkeypatch):
    monkeypatch.setattr(auth.settings, "admin_token", "admin-demo-token")
    assert require_admin("Bearer admin-demo-token") is None


def test_invalid_admin_bearer_token_is_rejected(monkeypatch):
    monkeypatch.setattr(auth.settings, "admin_token", "admin-demo-token")
    try:
        require_admin("Bearer wrong-token")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("invalid admin token was accepted")


def test_idempotency_key_is_required_and_bounded():
    assert require_idempotency_key("check-key-1") == "check-key-1"
    for value in (None, "x" * 129):
        try:
            require_idempotency_key(value)
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("invalid idempotency key was accepted")


def test_merchant_endpoint_rejects_missing_api_key():
    with TestClient(app) as client:
        response = client.get("/history/user-1")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_admin_endpoint_rejects_missing_bearer_token(monkeypatch):
    monkeypatch.setattr(auth.settings, "admin_token", "admin-demo-token")
    with TestClient(app) as client:
        response = client.get("/stats")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_rate_limit_is_scoped_to_both_merchant_and_ip():
    limiter = RateLimiter()
    limiter.enforce("checks", "merchant-1", "192.0.2.10", limit=1, window_seconds=60)
    limiter.enforce("checks", "merchant-2", "192.0.2.11", limit=1, window_seconds=60)

    try:
        limiter.enforce("checks", "merchant-1", "192.0.2.12", limit=1, window_seconds=60)
    except HTTPException as exc:
        assert exc.status_code == 429
        assert int(exc.headers["Retry-After"]) > 0
    else:
        raise AssertionError("merchant rate limit did not trigger")


def test_rate_limit_response_preserves_retry_after():
    limiter = RateLimiter()
    limiter.enforce("checks", "merchant-1", "192.0.2.10", limit=1, window_seconds=60)
    try:
        limiter.enforce("checks", "merchant-1", "192.0.2.10", limit=1, window_seconds=60)
    except HTTPException as exc:
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
        response = asyncio.run(http_error(request, exc))
        assert response.status_code == 429
        assert response.headers["retry-after"] == exc.headers["Retry-After"]
    else:
        raise AssertionError("rate limit did not trigger")


def test_rate_limit_is_scoped_to_ip_across_merchants():
    limiter = RateLimiter()
    limiter.enforce("checks", "merchant-1", "192.0.2.10", limit=1, window_seconds=60)

    try:
        limiter.enforce("checks", "merchant-2", "192.0.2.10", limit=1, window_seconds=60)
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("IP rate limit did not trigger")


def test_transaction_bounds_reject_invalid_amount_and_coordinates():
    data = {
        "user_id": "user-1",
        "device_id": "device-1",
        "amount": 0,
        "time": 1,
        "lat": 91,
        "lon": 0,
        "timestamp": "2026-11-16T12:00:00+05:30",
    }

    try:
        TransactionInput.model_validate(data)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid transaction bounds were accepted")
