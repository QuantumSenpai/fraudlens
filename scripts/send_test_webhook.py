import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.config import settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/v1/webhooks/razorpay")
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--payment-id", default="pay_test_local_sample")
    parser.add_argument("--event", choices=["order.paid", "payment.authorized", "payment.captured", "payment.failed"], default="payment.captured")
    parser.add_argument("--event-id", default="evt_fraudlens_local_test")
    args = parser.parse_args()
    if not settings.razorpay_webhook_secret:
        raise SystemExit("RAZORPAY_WEBHOOK_SECRET must be set in backend/.env")
    status = "failed" if args.event == "payment.failed" else "captured" if args.event in {"payment.captured", "order.paid"} else "authorized"
    payload = {
        "event": args.event,
        "payload": {
            "payment": {
                "entity": {
                    "id": args.payment_id,
                    "order_id": args.order_id,
                    "status": status,
                }
            }
        },
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(settings.razorpay_webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Razorpay-Signature": signature, "x-razorpay-event-id": args.event_id}
    try:
        response = httpx.post(args.url, content=raw_body, headers=headers, timeout=15.0)
    except httpx.HTTPError as exc:
        raise SystemExit(f"Webhook request failed: {type(exc).__name__}") from exc
    print(f"status={response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print("response_body=non_json")


if __name__ == "__main__":
    main()
