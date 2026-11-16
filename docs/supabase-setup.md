# Connected local setup

Verified on 2026-11-16 against Supabase project `qssgkrptiiaifxzsquos`.

## Database

Migrations 001 and 003–010 are applied and recorded in Supabase migration history. Migration 002 was skipped; the existing merchant creation script created one active `FraudLens Demo` merchant with a hashed API key.

All nine public application tables have RLS enabled and no client policies. The six application RPCs are executable by `service_role`, not `anon`, `authenticated`, or `PUBLIC`. Migration 010 pins their search paths and removes public client execution of the project's existing RLS event-trigger function. Existing transaction data and policies were preserved.

The security advisor reports only informational “RLS enabled, no policy” notices, which match this server-only design. The performance advisor reports unused indexes on the newly initialized database; no indexes were removed.

## Local configuration

`backend/.env` contains the existing Supabase and Razorpay test credentials, a generated admin token and webhook secret, and `MODEL_VERSION=xgb_live_v1`. The live-feature model artifact already existed. It is intended for demonstration and is not a validated production fraud model.

`frontend/.env.local` points to `http://127.0.0.1:8000` and contains the merchant API key, matching admin token, session secret, and separate `DEMO_PASSWORD` and `ADMIN_PASSWORD` login values. Both environment files are gitignored and owner-readable/writable only. Secrets were not copied into client code or documentation.

From the repository root, start the backend:

```sh
cd backend
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

In another terminal, start the built frontend:

```sh
cd frontend
npm run build
npm run start -- --hostname localhost --port 3000
```

Open `http://localhost:3000/access` for the merchant or `http://localhost:3000/access?role=admin` for the reviewer. Retrieve the corresponding password from `frontend/.env.local`.

## Verification

- 99 backend tests passed, including regressions for secret API keys, the actual PostgREST insert/upsert response format, high-value mandatory reviews, threshold boundaries, trusted-device discounts, and payment approval enforcement.
- 21 frontend tests passed, including invalidating decisions/payment state after edits and locking details during requests; the production frontend build passed.
- An isolated Chromium browser verified merchant/reviewer sign-in, the live dashboard and SSE connection, review/evaluation views, and no browser runtime errors.
- 14 live integration checks passed through the frontend proxy and real Supabase: model/database health, login and role isolation, signals, model checks, retry idempotency, structuring review, payment approval enforcement, Razorpay test-order creation and retry, review queue/resolution/feedback, admin statistics/evaluation, legacy statistics, and invalid webhook rejection.
- Temporary Supabase verification records were deleted. One unpaid Razorpay test order was created; no payment was charged or captured.
- After the high-value policy fix, ten additional live browser checks verified low-value ALLOW, high-value REVIEW, server-side payment refusal before approval, stale result invalidation after edits/location changes, the original reported check's payment refusal, reviewer rejection, and no runtime errors. Only the isolated verification records were cleaned up; user testing history was preserved.

## Remaining external setup

Public deployment and a real Razorpay callback/capture were not performed. For hosted webhooks, configure the deployed `/v1/webhooks/razorpay` URL in the Razorpay test dashboard using the generated `RAZORPAY_WEBHOOK_SECRET` from `backend/.env`. A local secret alone does not configure the provider.

The initial browser attempt encountered a repeating reload in the Turbopack development server; verification uses the production build. The development reload issue was not investigated as part of database setup.
