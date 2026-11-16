from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from schemas import CheckInput, CheckResponse
from services.client_ip import resolve_client_ip
from services.decision_engine import calculate_final_score, calculate_rule_score, resolve_decision
from services.db import get_supabase
from services.model_service import model_service
from services.live_features import build_live_features
from services.live_feed import publish_check
from services.rules import RuleContext, RuleResult, evaluate_rules
from services.rules.base import timestamp_for
from services.rules_config import RULES_CONFIG


def _rows(query: Any) -> list[dict[str, Any]]:
    try:
        return query.execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Decision data is unavailable") from exc


def _existing(client: Any, merchant_id: str, key: str) -> dict[str, Any] | None:
    rows = _rows(
        client.table("checks")
        .select("*")
        .eq("merchant_id", merchant_id)
        .eq("idempotency_key", key)
        .limit(1)
    )
    return rows[0] if rows else None


def _response(row: dict[str, Any]) -> CheckResponse:
    reasons = [
        {"rule": item["rule"], "detail": item["detail"], "weight": item["weight"]}
        for item in row.get("triggered_rules", [])
    ]
    return CheckResponse(
        check_id=str(row["id"]),
        decision=row["decision"],
        final_score=float(row["final_score"]),
        ml_score=float(row["ml_score"]),
        rule_score=int(row["rule_score"]),
        reasons=reasons,
        model_version=row["model_version"],
        ml_factors=row.get("ml_factors", []),
        latency_ms=int(row["latency_ms"]),
    )


def _load_context(client: Any, payload: CheckInput, now: datetime) -> RuleContext:
    try:
        data = client.rpc("check_context", {
            "p_user_id": payload.user_id,
            "p_device_id": payload.device_id,
            "p_now": now.isoformat(),
            "p_user_limit": RULES_CONFIG["context"]["user_history_limit"],
            "p_device_limit": RULES_CONFIG["context"]["device_decision_limit"],
            "p_payment_window_minutes": RULES_CONFIG["rules"]["FAILED_PAYMENT_BURST"]["window_minutes"],
        }).execute().data
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Decision data is unavailable") from exc
    device = data.get("device") if isinstance(data, dict) else None
    if not device:
        raise HTTPException(status_code=409, detail="Device signals must be registered before checking a payment")
    user_history = data["user_checks"] + data["legacy_transactions"]
    user_history.sort(key=lambda item: timestamp_for(item) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    first_seen = datetime.fromisoformat(device["first_seen"].replace("Z", "+00:00"))
    if first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=timezone.utc)
    device_age_days = max(0, int((now - first_seen).total_seconds() // 86400))
    return RuleContext(
        now=now,
        amount=payload.amount,
        user_id=payload.user_id,
        device_id=payload.device_id,
        lat=payload.lat,
        lon=payload.lon,
        user_history=user_history,
        known_device=any(row.get("device_id") == payload.device_id for row in user_history),
        device_user_count=data["device_user_count"],
        failed_payment_count=data["failed_payment_count"],
        device_age_days=device_age_days,
        device_timezone=device.get("timezone"),
        device_decisions=data["device_decisions"],
    )


def create_check(payload: CheckInput, merchant_id: str, idempotency_key: str, client_ip: str) -> CheckResponse:
    started = perf_counter()
    client = get_supabase()
    existing = _existing(client, merchant_id, idempotency_key)
    if existing:
        return _response(existing)

    now = datetime.now(timezone.utc)
    context = _load_context(client, payload, now)
    seconds_into_day = now.hour * 3600 + now.minute * 60 + now.second
    live_features = build_live_features(
        payload.amount,
        now,
        payload.payment_method,
        context.user_history,
        context.device_age_days * 24,
        context.device_user_count,
        payload.lat,
        payload.lon,
    )
    probability, ml_factors = model_service.predict_with_factors(payload.amount, seconds_into_day, live_features)
    ml_score = round(probability * 100, 2)
    results: list[RuleResult] = evaluate_rules(context, RULES_CONFIG)
    rule_score = calculate_rule_score(results)
    final_score = calculate_final_score(ml_score, rule_score, RULES_CONFIG)
    decision = resolve_decision(final_score, results, RULES_CONFIG)
    latency_ms = max(0, round((perf_counter() - started) * 1000))
    row = {
        "merchant_id": merchant_id,
        "idempotency_key": idempotency_key,
        "user_id": payload.user_id,
        "device_id": payload.device_id,
        "ip": client_ip,
        "amount": payload.amount,
        "currency": payload.currency,
        "payment_method": payload.payment_method,
        "lat": payload.lat,
        "lon": payload.lon,
        "ml_score": ml_score,
        "rule_score": rule_score,
        "final_score": final_score,
        "decision": decision,
        "triggered_rules": [
            {"rule": result.rule, "detail": result.detail, "weight": result.weight, "hard": result.hard}
            for result in results
        ],
        "model_version": model_service.version,
        "ml_factors": ml_factors,
        "latency_ms": latency_ms,
    }
    try:
        stored = client.table("checks").insert(row).select("*").single().execute().data
    except Exception:
        existing = _existing(client, merchant_id, idempotency_key)
        if existing:
            return _response(existing)
        raise HTTPException(status_code=503, detail="Decision could not be stored")
    response = _response(stored)
    publish_check({
        "check_id": str(stored["id"]),
        "user_id": stored["user_id"],
        "device_id": stored["device_id"],
        "amount": float(stored["amount"]),
        "currency": stored["currency"],
        "payment_method": stored["payment_method"],
        "decision": stored["decision"],
        "final_score": float(stored["final_score"]),
        "ml_score": float(stored["ml_score"]),
        "rule_score": int(stored["rule_score"]),
        "reasons": [reason.model_dump() for reason in response.reasons],
        "model_version": stored["model_version"],
        "latency_ms": int(stored["latency_ms"]),
        "created_at": stored.get("created_at"),
    })
    return response
