# Razorpay test-mode guide

FraudLens uses direct HTTP requests to Razorpay with `httpx`, which is already a backend dependency and avoids adding the SDK. The server uses the key secret for API authentication and signature checks. The frontend receives only the public key id.

## Configure test credentials

Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` in `backend/.env`. In every environment except the explicit `ENV=prod`, the key id must start with `rzp_test_`. Razorpay test transactions are simulated and do not move real money. Keep secrets server-side.

## Run a test checkout

From the repository root in PowerShell, activate the environment, configure `backend/.env` locally, apply all migrations in the Supabase SQL Editor, and create a merchant:

```powershell
conda activate fraudenv
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
notepad backend/.env
python scripts/create_merchant.py --name "FraudLens Demo"
$env:FRAUDLENS_API_KEY = Read-Host "Merchant API key"
Push-Location backend
python -m uvicorn main:app --port 8000 --no-proxy-headers
```

Keep the API running. In a second PowerShell window, run:

```powershell
conda activate fraudenv
$env:FRAUDLENS_API_KEY = Read-Host "Merchant API key"
$base = "http://127.0.0.1:8000"
$headers = @{ "X-API-Key" = $env:FRAUDLENS_API_KEY }
$demoId = [guid]::NewGuid().ToString()
$signal = @{ device_id = "demo-device-$demoId"; user_id = "demo-user-$demoId"; platform = "web"; user_agent = "FraudLens test"; screen = @{ width = 1280; height = 800 }; timezone = "Asia/Kolkata"; language = "en-IN" } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "$base/v1/signals" -Headers $headers -ContentType "application/json" -Body $signal
$headers["Idempotency-Key"] = [guid]::NewGuid().ToString()
$checkBody = @{ user_id = "demo-user-$demoId"; device_id = "demo-device-$demoId"; amount = 250; currency = "INR"; payment_method = "upi" } | ConvertTo-Json
$check = Invoke-RestMethod -Method Post -Uri "$base/v1/checks" -Headers $headers -ContentType "application/json" -Body $checkBody
$check | Select-Object check_id, decision, final_score, reasons
if ($check.decision -ne "ALLOW") { throw "Use an ALLOW check, or approve REVIEW in the admin queue" }
$headers["Idempotency-Key"] = [guid]::NewGuid().ToString()
$order = Invoke-RestMethod -Method Post -Uri "$base/v1/payments/order" -Headers $headers -ContentType "application/json" -Body (@{ check_id = $check.check_id } | ConvertTo-Json)
$order | Select-Object order_id, amount, currency, key_id
python scripts/send_test_webhook.py --order-id $order.order_id --event payment.captured
```

The order call reaches Razorpay only when valid test credentials are configured. The local signer tests FraudLens webhook handling; it is not an event delivered by Razorpay. A real Checkout payment requires the frontend or a temporary Checkout page, plus a publicly reachable webhook URL. After that payment, send the three Checkout callback fields to `/v1/payments/verify` and confirm `captured` from the webhook or Razorpay Dashboard.

1. Start the API and register a device, then call `/v1/checks`.
2. Use an `ALLOW` check or approve its `REVIEW` case before calling `/v1/payments/order`.
3. Give Razorpay Checkout the returned `order_id`, `amount`, `currency`, and `key_id`.
4. For test UPI, Razorpay documents `success@razorpay` for success and `failure@razorpay` for failure. UPI availability depends on the test account and supported Checkout flow.
5. For domestic card testing, Razorpay documents Visa `4100 2800 0000 1007` and Mastercard `5500 6700 0000 1002`; use a random CVV and future expiry. These are Razorpay test values, not customer data. Do not submit customer card or UPI information to FraudLens.
6. Send the Checkout callback fields to `/v1/payments/verify`. Treat `captured` as paid; `authorized` is not a final captured state.

Razorpay's current [Python integration guide](https://razorpay.com/docs/payments/server-integration/python/integration-steps/) lists the test card and UPI values and documents Checkout signature construction. Its [webhook verification guide](https://hdfcbank-collectnow-docs.razorpay.com/webhooks/validate-test/) requires HMAC-SHA256 over the exact raw request body and describes webhook retries and event ids.

## Test a webhook locally without a tunnel

Create a payment order through the API, then pass its order id to the local signer:

```powershell
python scripts/send_test_webhook.py --order-id order_id_from_api --event payment.captured
```

To verify replay handling, run the same command again. It uses the same event id by default, so the second response should report `duplicate: true`. Use `--event-id` to simulate a distinct event. The script reads the webhook secret from `backend/.env` and never prints it.

## Receive Razorpay webhooks on localhost

Start the API on port 8000, then in another terminal run either `ngrok http 8000` or `cloudflared tunnel --url http://localhost:8000`. Register the generated HTTPS URL plus `/v1/webhooks/razorpay` in Razorpay Dashboard Test Mode. Subscribe to `order.paid`, `payment.authorized`, `payment.captured`, and `payment.failed`, and set the webhook secret to the same server-side `RAZORPAY_WEBHOOK_SECRET`. Keep the tunnel process running while testing. Temporary tunnel URLs change when recreated.

Razorpay sends the original raw body and `X-Razorpay-Signature`; FraudLens validates the signature before parsing or updating payment data. The implementation stores payment/order identifiers and status only. It does not store card numbers, CVV, or UPI IDs.

Official tunnel instructions: [ngrok HTTP endpoints](https://ngrok.com/docs/gateway/endpoints/http) and [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
