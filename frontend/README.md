# FraudLens frontend

Next.js App Router frontend for the FraudLens fraud decision gateway. Public pages explain the flow. The merchant demo and reviewer workspace require separate frontend passwords, and all FastAPI credentials stay on the Next.js server.

## Run locally on macOS with zsh

From the repository root:

```zsh
cd frontend
npm ci
cp .env.example .env.local
```

Set the seven values in `frontend/.env.local`. Use `FRAUDLENS_API_URL=http://127.0.0.1:8000` and `SITE_URL=http://localhost:3000` for local development. Set `FRAUDLENS_API_KEY` to one demo merchant key, `FRAUDLENS_ADMIN_TOKEN` to the backend admin token, and choose distinct `DEMO_PASSWORD` and `ADMIN_PASSWORD` values. Generate `SESSION_SECRET` locally with `openssl rand -hex 32`. Keep all values server-side and never use a `NEXT_PUBLIC_` prefix. The example file has empty values by design.

Start the backend according to [backend/README.md](../backend/README.md), then run:

```zsh
cd frontend
npm run dev
```

Open `http://localhost:3000`. Use `/access` for the merchant demo and `/access?role=admin` for the reviewer workspace. The demo uses a random install ID in this site's local storage. The frontend assumes one merchant API key per deployment, which scopes that ID to the configured merchant. No card number, CVV, or UPI address enters a FraudLens form.

## Routes

| Route | Purpose | Access |
|---|---|---|
| `/` | Product landing page | Public |
| `/how-it-works` | Check and test payment flow | Public |
| `/privacy` | Product data-use note | Public |
| `/access` | Merchant or reviewer sign-in | Public, noindex |
| `/demo` | Signals, check, and test Checkout | Merchant session, noindex |
| `/admin` | Stats, live feed, reviews, evaluation | Admin session, noindex |
| `/api/session` | Sign in and sign out | Same-origin server route |
| `/api/gateway/[...path]` | Restricted FastAPI proxy | Session and route allowlist |
| `/api/feed` | Admin SSE proxy | Admin session |

`components/merchant-demo.tsx` owns the check and payment flow. `components/dashboard.tsx` owns the reviewer flow. `components/header.tsx`, `footer.tsx`, `brand.tsx`, `decision-badge.tsx`, `decision-stage.tsx`, `page-motion.tsx`, and `sign-out.tsx` share the visual and interaction system. `lib/types.ts` holds the API contract types; `lib/client-api.ts` handles browser errors; `lib/session.ts` and `lib/server-api.ts` keep credentials server-side. Tailwind v4 theme tokens, palette, spacing, type, motion, and signature responsive rules live in `app/globals.css`. Accessible shared primitives live in `components/ui`.

## Checks

```zsh
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
npm audit --omit=dev --audit-level=high
```

For a production build, set `SITE_URL` to the real HTTPS origin and serve Next.js over HTTPS so its `Secure` session cookie works. Public routes are indexable. Demo, access, admin, and API routes are noindex or disallowed. The session cookie is signed, httpOnly, sameSite lax, and expires after eight hours. Passwords and FastAPI credentials are read only on the server. A production deployment should add edge rate limiting to `/api/session` and use strong passwords.

## API constraints

The frontend follows [docs/api-contract.md](../docs/api-contract.md). It sends INR rupees to `POST /v1/checks`, receives Razorpay order amounts in paise, and passes only the public `key_id` to Checkout. It refuses any order key that lacks the `rzp_test_` prefix. `POST /v1/payments/verify` checks the Checkout signature, but only `captured` is displayed as paid.

The contract has no merchant `GET` endpoint for review approval or payment status. For a REVIEW, the `Check approval and continue` action retries `POST /v1/payments/order`; the backend returns an error until approved. After Checkout, `Refresh capture status` repeats `POST /v1/payments/verify` using the callback signature. Those are contract limits, not invented frontend states. The SSE feed has no replay after reconnecting.

Rules and thresholds are heuristics until evaluated. Synthetic or PaySim metrics are not real-world accuracy. FraudLens is a test-mode fraud decision layer, not a payment processor. Live Supabase, Razorpay, and deployed integration require configured credentials and were not proven by frontend unit tests.

## Refinement and verification

See [REFINEMENT.md](REFINEMENT.md) for the full environment inventory, changed paths, static asset audit, screenshots, limitations, and macOS zsh commands. See [CONTROL-INVENTORY.md](CONTROL-INVENTORY.md) for expected control outcomes.

The repeatable Chromium fixture suite runs with `npm run test:browser` after `npx playwright install chromium`. Stop other frontend dev servers first. It starts the existing app and a local synthetic API, with ephemeral credentials, and tests the real Next.js session and proxy boundaries. It does not verify Supabase persistence, real Razorpay Checkout, or provider webhooks.
