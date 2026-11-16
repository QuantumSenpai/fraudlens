import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
from services.auth import require_admin
from services import admin_service, live_feed
from services.config import settings


def _admin_auth():
    app.dependency_overrides[require_admin] = lambda: None


def _clear_admin_auth():
    app.dependency_overrides.pop(require_admin, None)


def test_pending_review_queue_excludes_resolved_checks(monkeypatch):
    calls = []

    class Database:
        def rpc(self, name, params):
            calls.append((name, params))
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=[{
                "id": "check-pending", "user_id": "user-1", "triggered_rules": [], "review": None,
            }]))

    monkeypatch.setattr(admin_service, "get_supabase", lambda: Database())
    _admin_auth()
    try:
        with TestClient(app) as client:
            response = client.get("/v1/admin/reviews?status=pending")
    finally:
        _clear_admin_auth()

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "check-pending"
    assert response.json()[0]["reasons"] == []
    assert calls == [("list_reviews", {"p_status": "pending", "p_limit": 50, "p_offset": 0})]


def test_review_resolution_writes_atomic_rpc_payload(monkeypatch):
    rpc_calls = []
    check_id = "00000000-0000-0000-0000-000000000001"

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
            if self.table == "checks":
                    return SimpleNamespace(data=[{"id": check_id, "decision": "REVIEW"}])
            return SimpleNamespace(data=[])

    class Database:
        def table(self, name):
            return Query(name)

        def rpc(self, name, params):
            rpc_calls.append((name, params))
            return SimpleNamespace(execute=lambda: SimpleNamespace(data={"check_id": check_id, "outcome": "reject", "label": "fraud"}))

    monkeypatch.setattr(admin_service, "get_supabase", lambda: Database())
    _admin_auth()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/v1/admin/reviews/{check_id}",
                json={"outcome": "reject", "reviewer": "analyst-1", "note": "confirmed test scenario"},
            )
    finally:
        _clear_admin_auth()

    assert response.status_code == 200
    assert response.json()["label"] == "fraud"
    assert rpc_calls == [("resolve_review", {
        "p_check_id": check_id,
        "p_reviewer": "analyst-1",
        "p_outcome": "reject",
        "p_note": "confirmed test scenario",
    })]


def test_admin_stats_and_evaluation_use_database_aggregates(monkeypatch):
    calls = []

    class Database:
        def rpc(self, name, params):
            calls.append((name, params))
            result = {"total_checks": 2} if name == "admin_stats" else {"labels_total": 1, "precision": 1.0}
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))

    monkeypatch.setattr(admin_service, "get_supabase", lambda: Database())
    _admin_auth()
    try:
        with TestClient(app) as client:
            stats_response = client.get("/v1/admin/stats")
            eval_response = client.get("/v1/admin/evaluation")
    finally:
        _clear_admin_auth()

    assert stats_response.status_code == eval_response.status_code == 200
    assert stats_response.json()["total_checks"] == 2
    assert eval_response.json()["labels_total"] == 1
    assert calls == [("admin_stats", {}), ("admin_evaluation", {})]


def test_live_feed_delivers_check_events_to_subscribers():
    event_queue = live_feed.subscribe()
    live_feed.publish_check({"check_id": "check-1", "decision": "ALLOW"})

    try:
        assert event_queue.get_nowait() == {"check_id": "check-1", "decision": "ALLOW"}
    finally:
        live_feed.unsubscribe(event_queue)


def test_sse_formats_new_check_event_and_closes_subscription():
    from routes.admin import _events

    event_queue = live_feed.subscribe()
    live_feed.publish_check({"check_id": "check-1", "decision": "ALLOW"})

    async def next_event():
        stream = _events(event_queue)
        value = await stream.__anext__()
        await stream.aclose()
        return value

    assert asyncio.run(next_event()) == 'id: check-1\nevent: check\ndata: {"check_id":"check-1","decision":"ALLOW"}\n\n'


def test_admin_routes_require_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "admin-token-value")

    with TestClient(app) as client:
        response = client.get("/v1/admin/reviews?status=pending")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_review_queue_rejects_unbounded_page(monkeypatch):
    _admin_auth()
    try:
        with TestClient(app) as client:
            response = client.get("/v1/admin/reviews?limit=1000")
    finally:
        _clear_admin_auth()

    assert response.status_code == 422
