from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
from schemas import DeviceSignalsInput
from services.auth import require_merchant
from services import device_service
from services.device_service import compute_trust_score, record_device_signal


def test_device_trust_score_uses_age_shared_users_and_prior_decisions():
    now = datetime(2026, 11, 16, tzinfo=timezone.utc)
    score = compute_trust_score(
        now - timedelta(days=40),
        linked_users=3,
        decisions=["ALLOW", "ALLOW", "BLOCK"],
        now=now,
    )

    assert score == 26


def test_signals_schema_requires_coordinates_as_a_pair():
    data = {
        "device_id": "device-1",
        "user_id": "user-1",
        "platform": "web",
        "user_agent": "Mozilla/5.0",
        "screen": {"width": 1440, "height": 900, "pixel_ratio": 2},
        "timezone": "Asia/Kolkata",
        "language": "en-IN",
        "lat": 12.97,
    }

    try:
        DeviceSignalsInput.model_validate(data)
    except ValueError:
        pass
    else:
        raise AssertionError("unpaired coordinates were accepted")


def test_signals_schema_accepts_all_platforms():
    base = {
        "device_id": "device-1",
        "user_id": "user-1",
        "user_agent": "Mozilla/5.0",
        "screen": {"width": 1440, "height": 900},
        "timezone": "Asia/Kolkata",
        "language": "en-IN",
    }

    for platform in ("web", "mobile", "extension"):
        assert DeviceSignalsInput.model_validate({**base, "platform": platform}).platform == platform


def test_record_signal_upserts_device_link_and_trust_score(monkeypatch):
    first_seen = (datetime.now(timezone.utc) - timedelta(days=50)).isoformat()
    calls = []

    class Query:
        def __init__(self, table):
            self.table = table
            self.operation = ""
            self.wrote = False

        def upsert(self, payload, **kwargs):
            self.operation = "upsert"
            self.wrote = True
            calls.append((self.table, self.operation, payload, kwargs))
            return self

        def update(self, payload):
            self.operation = "update"
            self.wrote = True
            calls.append((self.table, self.operation, payload, {}))
            return self

        def select(self, *_args, **_kwargs):
            self.operation = "select"
            return self

        def single(self):
            return self

        def eq(self, *_args):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args):
            return self

        def execute(self):
            if self.table == "devices" and self.wrote:
                return SimpleNamespace(data={"first_seen": first_seen, "last_seen": first_seen})
            if self.table == "device_users" and self.operation == "select":
                return SimpleNamespace(count=1, data=[])
            if self.table == "checks":
                return SimpleNamespace(data=[{"decision": "ALLOW"}])
            return SimpleNamespace(data=[])

    class Database:
        def table(self, name):
            return Query(name)

    payload = DeviceSignalsInput.model_validate({
        "device_id": "device-1",
        "user_id": "user-1",
        "platform": "mobile",
        "user_agent": "Mobile browser",
        "screen": {"width": 390, "height": 844},
        "timezone": "Asia/Kolkata",
        "language": "en-IN",
        "lat": 12.97,
        "lon": 77.59,
    })
    monkeypatch.setattr(device_service, "get_supabase", Database)

    result = record_device_signal(payload, "203.0.113.9")

    assert result["trust_score"] == 78
    device_write = next(call for call in calls if call[0] == "devices" and call[1] == "upsert")
    assert device_write[2]["last_ip"] == "203.0.113.9"
    assert device_write[2]["last_lat"] == 12.97
    assert device_write[2]["screen"]["width"] == 390
    assert any(call[0] == "device_users" and call[1] == "upsert" for call in calls)


def test_signals_ignore_untrusted_forwarded_ip_and_accept_all_platforms(monkeypatch):
    from routes import signals

    captured = {}
    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}
    monkeypatch.setattr(
        signals,
        "record_device_signal",
        lambda payload, client_ip: captured.update({"payload": payload, "client_ip": client_ip}) or {
            "device_id": payload.device_id,
            "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-11-16T00:00:00+00:00",
            "trust_score": 50,
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/signals",
                headers={"X-API-Key": "fl_demo_key_with_enough_length", "X-Forwarded-For": "203.0.113.9, 10.0.0.1"},
                json={
                    "device_id": "device-1",
                    "user_id": "user-1",
                    "platform": "extension",
                    "user_agent": "FraudLens extension test",
                    "screen": {"width": 1280, "height": 800},
                    "timezone": "Asia/Kolkata",
                    "language": "en-IN",
                },
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 200
    assert captured["client_ip"] == "0.0.0.0"
    assert captured["payload"].platform == "extension"
    assert response.json()["trust_score"] == 50


def test_production_rejects_ip_override(monkeypatch):
    from routes import signals
    from services.config import settings

    monkeypatch.setattr(settings, "env", "prod")
    app.dependency_overrides[require_merchant] = lambda: {"id": "merchant-1"}

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/signals",
                headers={"X-API-Key": "fl_demo_key_with_enough_length"},
                json={
                    "device_id": "device-1",
                    "user_id": "user-1",
                    "platform": "web",
                    "user_agent": "Mozilla/5.0",
                    "screen": {"width": 1280, "height": 800},
                    "timezone": "Asia/Kolkata",
                    "language": "en-IN",
                    "ip_override": "198.51.100.2",
                },
            )
    finally:
        app.dependency_overrides.pop(require_merchant, None)

    assert response.status_code == 403


def test_cloudflare_client_ip_takes_precedence_for_trusted_proxy(monkeypatch):
    from services.client_ip import resolve_client_ip
    from services.config import settings
    from starlette.requests import Request

    monkeypatch.setattr(settings, "trusted_proxy_ips", "10.0.0.1")

    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/v1/signals",
        "headers": [
            (b"cf-connecting-ip", b"203.0.113.12"),
            (b"x-forwarded-for", b"198.51.100.8, 10.0.0.1"),
        ],
        "client": ("10.0.0.1", 8080),
    })

    assert resolve_client_ip(request) == "203.0.113.12"
    monkeypatch.setattr(settings, "trusted_proxy_ips", "")
    assert resolve_client_ip(request) == "10.0.0.1"
