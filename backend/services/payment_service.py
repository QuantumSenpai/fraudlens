import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx
from fastapi import HTTPException

from services.config import settings
from services.db import get_supabase
from services.rules_config import RULES_CONFIG


def validate_payment_settings(config: Any = settings) -> None:
    if not config.razorpay_key_id or not config.razorpay_key_secret:
        raise ValueError("Razorpay payment credentials are not configured")
    if config.env.lower() != "prod" and not config.razorpay_key_id.startswith("rzp_test_"):
        raise ValueError("Payment endpoints require a Razorpay test key unless ENV=prod")


def checkout_signature(order_id: str, payment_id: str, secret: str) -> str:
    message = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def webhook_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def _data(query: Any) -> list[dict[str, Any]]:
    try:
        return query.execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Payment data is unavailable") from exc


def _stored_order(payment: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": payment["razorpay_order_id"],
        "amount": int((Decimal(str(payment["amount"])) * 100).quantize(Decimal("1"))),
        "currency": "INR",
        "key_id": settings.razorpay_key_id,
    }


def _create_remote_order(amount: int, currency: str, receipt: str) -> dict[str, Any]:
    try:
        response = httpx.post(
            "https://api.razorpay.com/v1/orders",
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            json={"amount": amount, "currency": currency, "receipt": receipt},
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or not body.get("id"):
            raise ValueError("Razorpay order response is invalid")
        return body
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Razorpay order creation failed") from exc


def create_payment_order(check_id: str, idempotency_key: str, merchant_id: str) -> dict[str, Any]:
    try:
        validate_payment_settings()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    client = get_supabase()
    checks = _data(
        client.table("checks")
        .select("id,merchant_id,decision,amount,currency")
        .eq("id", check_id)
        .eq("merchant_id", merchant_id)
        .limit(1)
    )
    if not checks:
        raise HTTPException(status_code=404, detail="Check not found")
    check = checks[0]
    if check["decision"] == "BLOCK":
        raise HTTPException(status_code=409, detail="Blocked checks cannot create payment orders")
    high_amount = RULES_CONFIG["rules"]["HIGH_AMOUNT"]
    if high_amount["enabled"] and Decimal(str(check["amount"])) >= Decimal(str(high_amount.get("block_threshold", "Infinity"))):
        raise HTTPException(status_code=409, detail="Payment amount meets or exceeds the hard limit")
    if (
        check["decision"] == "ALLOW"
        and high_amount["enabled"]
        and high_amount.get("hard", False)
        and Decimal(str(check["amount"])) > Decimal(str(high_amount["threshold"]))
    ):
        raise HTTPException(status_code=409, detail="High-value payment requires a new fraud check and reviewer approval")
    if check["decision"] == "REVIEW":
        approved = _data(
            client.table("reviews")
            .select("outcome")
            .eq("check_id", check_id)
            .eq("outcome", "approve")
            .limit(1)
        )
        if not approved:
            raise HTTPException(status_code=409, detail="Review approval is required before payment")
    existing = _data(
        client.table("payments")
        .select("razorpay_order_id,amount")
        .eq("check_id", check_id)
        .eq("idempotency_key", idempotency_key)
        .limit(1)
    )
    if existing:
        return _stored_order(existing[0])
    currency = check.get("currency") or "INR"
    if currency != "INR":
        raise HTTPException(status_code=422, detail="Razorpay order integration currently supports INR only")
    amount_paise = int((Decimal(str(check["amount"])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    remote = _create_remote_order(amount_paise, currency, check_id)
    row = {
        "check_id": check_id,
        "idempotency_key": idempotency_key,
        "razorpay_order_id": remote["id"],
        "amount": str(check["amount"]),
        "status": "created",
    }
    try:
        client.table("payments").insert(row).execute()
    except Exception as exc:
        existing = _data(
            client.table("payments")
            .select("razorpay_order_id,amount")
            .eq("check_id", check_id)
            .eq("idempotency_key", idempotency_key)
            .limit(1)
        )
        if existing:
            return _stored_order(existing[0])
        raise HTTPException(status_code=503, detail="Payment order could not be stored") from exc
    return {
        "order_id": remote["id"],
        "amount": amount_paise,
        "currency": currency,
        "key_id": settings.razorpay_key_id,
    }


def _event_key(event_id: str | None, raw_body: bytes) -> str:
    return event_id or hashlib.sha256(raw_body).hexdigest()


def process_webhook(event: dict[str, Any], event_id: str | None, raw_body: bytes) -> dict[str, bool]:
    event_type = event.get("event")
    status_by_event = {
        "order.paid": "captured",
        "payment.authorized": "authorized",
        "payment.captured": "captured",
        "payment.failed": "failed",
    }
    target_status = status_by_event.get(event_type)
    if target_status is None:
        return {"received": True, "duplicate": False}
    payload = event.get("payload") or {}
    payment_entity = ((payload.get("payment") or {}).get("entity") or {})
    order_entity = ((payload.get("order") or {}).get("entity") or {})
    order_id = payment_entity.get("order_id") or order_entity.get("id")
    payment_id = payment_entity.get("id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Webhook order reference is missing")
    client = get_supabase()
    dedupe_id = _event_key(event_id, raw_body)
    duplicate = _data(
        client.table("razorpay_webhook_events")
        .select("event_id")
        .eq("event_id", dedupe_id)
        .limit(1)
    )
    if duplicate:
        return {"received": True, "duplicate": True}
    payments = _data(
        client.table("payments")
        .select("id,status")
        .eq("razorpay_order_id", order_id)
        .limit(1)
    )
    if not payments:
        raise HTTPException(status_code=404, detail="Payment order not found")
    current = payments[0]
    rank = {"created": 0, "failed": 1, "authorized": 2, "captured": 3}
    current_rank = rank.get(current.get("status", "created"), 0)
    target_rank = rank[target_status]
    update = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if target_rank > current_rank:
        update["status"] = target_status
    if payment_id and target_rank >= current_rank:
        update["razorpay_payment_id"] = payment_id
    try:
        client.table("payments").update(update).eq("id", current["id"]).execute()
        client.table("razorpay_webhook_events").insert({"event_id": dedupe_id, "event_type": event_type}).execute()
    except Exception as exc:
        existing = _data(
            client.table("razorpay_webhook_events")
            .select("event_id")
            .eq("event_id", dedupe_id)
            .limit(1)
        )
        if existing:
            return {"received": True, "duplicate": True}
        raise HTTPException(status_code=503, detail="Webhook update could not be stored") from exc
    return {"received": True, "duplicate": False}


def verify_checkout_payment(order_id: str, payment_id: str, signature: str, merchant_id: str) -> dict[str, Any]:
    try:
        validate_payment_settings()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    client = get_supabase()
    rows = _data(
        client.table("payments")
        .select("id,check_id,razorpay_order_id,status")
        .eq("razorpay_order_id", order_id)
        .limit(1)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Payment order not found")
    payment = rows[0]
    checks = _data(
        client.table("checks")
        .select("id")
        .eq("id", payment["check_id"])
        .eq("merchant_id", merchant_id)
        .limit(1)
    )
    if not checks:
        raise HTTPException(status_code=404, detail="Payment order not found")
    expected = checkout_signature(payment["razorpay_order_id"], payment_id, settings.razorpay_key_secret)
    if not hmac.compare_digest(expected, signature.lower()):
        raise HTTPException(status_code=401, detail="Invalid payment signature")
    status = payment.get("status", "created")
    if status == "created":
        status = "authorized"
        try:
            client.table("payments").update({
                "razorpay_payment_id": payment_id,
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", payment["id"]).execute()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Payment verification could not be stored") from exc
    return {"order_id": payment["razorpay_order_id"], "payment_id": payment_id, "status": status}
