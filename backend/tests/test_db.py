import json
from datetime import datetime, timezone

import httpx
from postgrest import SyncPostgrestClient

from schemas import CheckInput, DeviceSignalsInput
from services import check_service, db, device_service


def test_server_client_accepts_supabase_secret_keys(monkeypatch):
    monkeypatch.setattr(db.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(db.settings, "supabase_key", "sb_secret_synthetic_test_key")
    db._client.cache_clear()
    try:
        client = db.get_supabase()
        assert client.table("merchants").select("id") is not None
    finally:
        db._client.cache_clear()


def test_signal_storage_uses_real_postgrest_write_response(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    def respond(request):
        if request.method == "POST" and request.url.path.endswith("/devices"):
            return httpx.Response(201, json=[{"first_seen": now, "last_seen": now}])
        return httpx.Response(200, json=[], headers={"Content-Range": "*/0"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        client = SyncPostgrestClient("https://example.supabase.co/rest/v1", http_client=http)
        monkeypatch.setattr(device_service, "get_supabase", lambda: client)
        result = device_service.record_device_signal(DeviceSignalsInput(
            device_id="sdk-test-device", user_id="sdk-test-user", platform="web",
            user_agent="SDK regression test", screen={"width": 1440, "height": 900},
            timezone="UTC", language="en",
        ), "127.0.0.1")
    assert result["first_seen"] == now
    assert result["trust_score"] == 50


def test_check_storage_uses_real_postgrest_write_response(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    def respond(request):
        if request.url.path.endswith("/rpc/check_context"):
            return httpx.Response(200, json={
                "device": {"first_seen": now, "timezone": "UTC"},
                "user_checks": [], "legacy_transactions": [], "device_user_count": 1,
                "device_decisions": [], "failed_payment_count": 0,
            })
        if request.method == "POST":
            return httpx.Response(201, json=[{**json.loads(request.content), "id": "sdk-test-check"}])
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        client = SyncPostgrestClient("https://example.supabase.co/rest/v1", http_client=http)
        monkeypatch.setattr(check_service, "get_supabase", lambda: client)
        monkeypatch.setattr(check_service.model_service, "predict_with_factors", lambda *args: (0.01, []))
        result = check_service.create_check(CheckInput(
            user_id="sdk-test-user", device_id="sdk-test-device", amount=250, payment_method="upi",
        ), "sdk-test-merchant", "sdk-test-idempotency", "127.0.0.1")
    assert result.check_id == "sdk-test-check"
    assert result.decision == "ALLOW"
