import json
import hmac
import re

from fastapi import APIRouter, Depends, HTTPException, Request

from schemas import (
    PaymentOrderInput,
    PaymentOrderResponse,
    PaymentVerificationInput,
    PaymentVerificationResponse,
)
from services.auth import require_idempotency_key, require_merchant
from services.client_ip import resolve_client_ip
from services.config import settings
from services.payment_service import (
    create_payment_order,
    process_webhook,
    validate_payment_settings,
    verify_checkout_payment,
    webhook_signature,
)
from services.rate_limit import rate_limiter

router = APIRouter()


def _require_payment_settings() -> None:
    try:
        validate_payment_settings(settings)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/v1/payments/order", response_model=PaymentOrderResponse)
def create_order(
    payload: PaymentOrderInput,
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
    merchant: dict = Depends(require_merchant),
):
    _require_payment_settings()
    client_ip = resolve_client_ip(request)
    rate_limiter.enforce("payments", str(merchant["id"]), client_ip, limit=10, window_seconds=60)
    return create_payment_order(str(payload.check_id), idempotency_key, str(merchant["id"]))


@router.post("/v1/payments/verify", response_model=PaymentVerificationResponse)
def verify_payment(
    payload: PaymentVerificationInput,
    request: Request,
    merchant: dict = Depends(require_merchant),
):
    _require_payment_settings()
    client_ip = resolve_client_ip(request)
    rate_limiter.enforce("payments", str(merchant["id"]), client_ip, limit=10, window_seconds=60)
    return verify_checkout_payment(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
        str(merchant["id"]),
    )


@router.post("/v1/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    if not settings.razorpay_webhook_secret:
        raise HTTPException(status_code=503, detail="Razorpay webhook is not configured")
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > 1_000_000):
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    raw_body = await request.body()
    if len(raw_body) > 1_000_000:
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    expected = webhook_signature(raw_body, settings.razorpay_webhook_secret)
    if not hmac.compare_digest(expected, signature.lower()):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    event_id = request.headers.get("x-razorpay-event-id")
    if event_id and len(event_id) > 160:
        raise HTTPException(status_code=400, detail="Invalid webhook event id")
    return process_webhook(event, event_id, raw_body)
