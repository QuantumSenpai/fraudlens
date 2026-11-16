from fastapi.testclient import TestClient

from main import app
from services.model_service import ModelService


def test_health_reports_model_and_database_state(monkeypatch):
    monkeypatch.setattr("main.db_reachable", lambda: False)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model_loaded": True,
        "db_reachable": False,
    }


def test_responses_include_request_id_and_errors_are_structured():
    with TestClient(app) as client:
        response = client.get("/not-a-route")

    assert response.status_code == 404
    assert response.headers["x-request-id"]
    assert response.headers["server-timing"].startswith("app;dur=")
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Resource not found",
    }
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_legacy_model_predicts_with_numpy_and_returns_factors():
    service = ModelService("xgb_creditcard_v1")
    service.load()
    score, factors = service.predict_with_factors(5000, 43200)

    assert 0 <= score <= 1
    assert len(factors) == 5
    assert all("feature" in factor and "contribution" in factor for factor in factors)
