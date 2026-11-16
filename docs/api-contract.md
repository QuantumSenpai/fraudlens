# FraudLens API contract

Base path is the API origin. JSON requests use `Content-Type: application/json`. Amounts on checks are INR rupees. The Razorpay order response amount is paise.

## Authentication headers

| Header | Used by | Value |
|---|---|---|
| `X-API-Key` | Merchant routes | Merchant API key created by `scripts/create_merchant.py` |
| `Idempotency-Key` | `POST /v1/checks`, `POST /v1/payments/order` | Unique per logical client operation, max 128 characters |
| `Authorization` | Admin routes | `Bearer <ADMIN_TOKEN>` |
| `X-Razorpay-Signature` | Razorpay webhook | HMAC-SHA256 hex digest over the exact raw request body |
| `x-razorpay-event-id` | Razorpay webhook | Optional provider event id; raw-body SHA-256 is used if absent |

Merchant routes are authenticated by API key and are rate-limited by merchant and client IP: checks 60/minute, payment order and verify 10/minute. Rate limits are in-memory per process. Admin routes require the bearer token. Webhook requests are authenticated by the signature, not the merchant API key.

## Health

### `GET /health`

No authentication.

```json
{
  "status": "ok",
  "model_loaded": true,
  "db_reachable": true
}
```

## Signals

### `POST /v1/signals`

Headers: `X-API-Key`.

The JS SDK, PWA, and extension send the same shape. `lat` and `lon` are optional and must be sent together. `ip_override` is intended only for local testing and is rejected when `ENV=prod`; normally the server uses the proxy/client IP.

```json
{
  "device_id": "merchant-scoped-install-id",
  "user_id": "merchant-user-42",
  "platform": "web",
  "user_agent": "Mozilla/5.0 ...",
  "screen": {"width": 1440, "height": 900, "pixel_ratio": 2},
  "timezone": "Asia/Kolkata",
  "language": "en-IN",
  "lat": 12.9716,
  "lon": 77.5946
}
```

`platform` is `web`, `mobile`, or `extension`. `screen.width` and `screen.height` must be from 1 to 16384; `pixel_ratio`, when present, must be greater than 0 and at most 10. `user_agent` max length is 512; time zone max 64; language max 35; ids max 160.

Response:

```json
{
  "device_id": "merchant-scoped-install-id",
  "first_seen": "2026-11-16T10:00:00+00:00",
  "last_seen": "2026-11-16T10:05:00+00:00",
  "trust_score": 50
}
```

## Decision check

### `POST /v1/checks`

Headers: `X-API-Key`, `Idempotency-Key`. Register signals before the first check for a device.

```json
{
  "user_id": "merchant-user-42",
  "device_id": "merchant-scoped-install-id",
  "amount": 1250.5,
  "currency": "INR",
  "payment_method": "upi",
  "lat": 12.9716,
  "lon": 77.5946
}
```

`amount` must be finite, greater than 0 and less than 10,000,000. `currency` is a 3-character uppercase code. `payment_method` is `upi`, `card`, `netbanking`, or `wallet`. Coordinates are optional, paired, and range-checked.

Response:

```json
{
  "check_id": "00000000-0000-0000-0000-000000000001",
  "decision": "REVIEW",
  "final_score": 30.8,
  "ml_score": 12.5,
  "rule_score": 77,
  "reasons": [
    {"rule": "STRUCTURING", "detail": "3 transactions between 90000 and 100000 within 24 hours", "weight": 35}
  ],
  "model_version": "xgb_live_v1",
  "ml_factors": [
    {"feature": "amount", "contribution": 0.2}
  ],
  "latency_ms": 24
}
```

`decision` is `ALLOW`, `REVIEW`, or `BLOCK`. `ml_factors` contains up to five XGBoost raw-margin contributions; positive values increase the model margin and are not probability percentages. Reusing the same idempotency key for the same merchant returns the stored check response.

## Payments

### `POST /v1/payments/order`

Headers: `X-API-Key`, `Idempotency-Key`. The `check_id` must belong to the merchant. `BLOCK` is rejected. `REVIEW` requires an approving review. Only INR orders are supported.

```json
{"check_id": "00000000-0000-0000-0000-000000000001"}
```

Response:

```json
{
  "order_id": "order_test_example",
  "amount": 125050,
  "currency": "INR",
  "key_id": "rzp_test_public_key_id"
}
```

`amount` is paise. The response includes only the public key id; never send the Razorpay key secret to the client. Repeating the idempotency key for the same check returns the saved order.

### `POST /v1/payments/verify`

Headers: `X-API-Key`.

```json
{
  "razorpay_order_id": "order_test_example",
  "razorpay_payment_id": "pay_test_example",
  "razorpay_signature": "<64-character-checkout-signature>"
}
```

The backend looks up the server-stored order id and verifies HMAC-SHA256 of `stored_order_id|razorpay_payment_id` with the server key secret. It returns the stored status, setting it to `authorized` on successful checkout verification if no webhook has already advanced it.

```json
{"order_id": "order_test_example", "payment_id": "pay_test_example", "status": "authorized"}
```

Statuses are `created`, `authorized`, `captured`, or `failed`. Treat only `captured` as paid.

### `POST /v1/webhooks/razorpay`

No API key. Headers: `X-Razorpay-Signature`; optional `x-razorpay-event-id`. The signature covers the exact raw body. Supported events: `order.paid`, `payment.authorized`, `payment.captured`, `payment.failed`. The endpoint acknowledges valid unsupported event types without changing a payment. Duplicate events return `{ "received": true, "duplicate": true }`.

Example successful acknowledgement:

```json
{"received": true, "duplicate": false}
```

FraudLens stores order/payment identifiers and status only. It does not store card number, CVV, or UPI address.

## Admin and live feed

Every admin endpoint uses `Authorization: Bearer <ADMIN_TOKEN>`.

### `GET /v1/admin/reviews?status=pending`

`status` is `pending` (default), `reviewed`, or `all`. `limit` defaults to 50 and is capped at 100; `offset` defaults to 0. Returns review checks with scores, rule reasons, and a `review` object (null when pending).

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000001",
    "user_id": "merchant-user-42",
    "device_id": "merchant-scoped-install-id",
    "amount": 95000,
    "currency": "INR",
    "payment_method": "upi",
    "final_score": 38.5,
    "ml_score": 12.5,
    "rule_score": 77,
    "triggered_rules": [],
    "model_version": "xgb_live_v1",
    "created_at": "2026-11-16T10:05:00+00:00",
    "reasons": [],
    "review": null
  }
]
```

### `POST /v1/admin/reviews/{check_id}`

```json
{"outcome": "approve", "reviewer": "analyst-1", "note": "Verified with merchant"}
```

`outcome` is `approve` or `reject`; reviewer is 1–160 characters (defaults to `admin`); note is optional and at most 2000 characters. Approval creates a `legit` feedback label; rejection creates `fraud`, both with source `reviewer`. A check can be resolved once.

### `GET /v1/admin/stats`

Returns `total_checks`, `decision_split` (`ALLOW`, `REVIEW`, `BLOCK`), `flagged_count`, `flagged_rate_percent`, `top_triggered_rules`, `average_latency_ms`, `p95_scoring_latency_ms`, and 24 `last_24h_hourly_counts` buckets. Saved latency covers context loading and scoring before the insert. The `Server-Timing` response header and request log cover the full API path. Stats are cached for up to five seconds per process.

### `GET /v1/admin/evaluation`

Returns labeled-case confusion counts and `precision`, `recall`, and `false_positive_rate`. `REVIEW` and `BLOCK` are treated as positive/flagged predictions; `ALLOW` is treated as negative. Ratios are null when their denominator is zero.

### `GET /v1/admin/feed`

Returns `text/event-stream`. Each new check is sent as an `event: check` with `id: <check_id>` and a compact JSON `data` record containing decision, scores, reasons, payment method, user/device ids, model version, and latency. `: keepalive` comments are sent every 15 seconds. The in-process feed is single-instance and has no replay buffer after disconnect.

## Legacy endpoints

`POST /predict` retains the legacy transaction fields (`user_id`, `device_id`, `amount`, `time`, `lat`, `lon`, `timestamp`) and legacy scoring fields, with additive `model_version` and `ml_factors`. `GET /history/{user_id}?limit=20` requires `X-API-Key`. `GET /stats` requires the admin bearer token and returns the legacy transaction totals/recent list.

## Errors

Every error includes `X-Request-ID` and a response body:

```json
{
  "error": {"code": "unauthorized", "message": "Authentication required"},
  "request_id": "00000000-0000-0000-0000-000000000001"
}
```

| HTTP | Error code | Common reason |
|---:|---|---|
| 400 | `request_failed` | Missing/invalid idempotency key or malformed webhook JSON |
| 401 | `unauthorized` | Invalid API/admin/webhook/payment signature |
| 403 | `forbidden` | Production IP override or other denied operation |
| 404 | `not_found` | Check/payment order not found |
| 409 | `conflict` | Device missing, blocked check, pending review, or already resolved review |
| 413 | `request_failed` | Webhook body exceeds 1 MB |
| 422 | `validation_error` or `request_failed` | Invalid schema or unsupported currency |
| 429 | `rate_limited` | Rate limit; response includes `Retry-After` |
| 500 | `internal_error` | Unexpected server error |
| 502 | `request_failed` | Razorpay order API failure |
| 503 | `service_unavailable` | Missing configuration, database, or storage issue |

## Client signal collection specification

All three clients should send the same `POST /v1/signals` shape. Generate a random merchant-scoped install id and persist it in the platform's normal local storage (web/PWA local storage or IndexedDB; extension storage for extensions). It should survive ordinary visits but may change after clearing storage or reinstalling. Do not use canvas, audio, font, or other invasive fingerprinting. Do not use a cross-merchant identifier.

Collect the user id from the merchant's own authenticated session; `navigator.userAgent`; `screen.width`, `screen.height`, and `devicePixelRatio`; `Intl.DateTimeFormat().resolvedOptions().timeZone`; `navigator.language`; platform label; and optional location only after the merchant obtains the appropriate user permission. Send only rounded/coarse coordinates if the merchant's UX does not need precise location. Do not collect payment instrument values.

Use `platform: "web"` for desktop browsers, `"mobile"` for mobile browser/PWA, and `"extension"` for browser extensions. Register each exact origin in `ALLOWED_ORIGINS`; CORS does not protect the API key. A browser bundle or extension package cannot keep a long-lived merchant API key secret. Use a merchant-owned backend proxy for real deployments.
