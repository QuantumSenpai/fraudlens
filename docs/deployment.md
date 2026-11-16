# Render and Vercel deployment

The frontend is the Next.js app in `frontend/`; the FastAPI backend is in `backend/`. Deploying the repository root as Vercel's “Other” framework produces an empty static deployment and a 404 instead of the app.

## Live deployment, verified 2026-11-16

- Website: https://fraudlens-ml.vercel.app
- Merchant access: https://fraudlens-ml.vercel.app/access
- Reviewer access: https://fraudlens-ml.vercel.app/access?role=admin
- Backend health: https://fraudlens-api-ocjj.onrender.com/health
- Render service: `srv-dbtikt6i0phs73f1d370`, free plan, Singapore.
- Both platforms use the verified `main` branch. Render automatically rebuilds for `backend/**` changes.
- Seven server-side production variables are configured in Vercel; backend credentials are in the Render secret file. The requested local login passwords were retained for hosted access.

The public landing/access routes return HTTP 200. Render health reports `model_loaded=true` and `db_reachable=true`. An isolated Chromium browser verified both role logins, actual Supabase-backed low/high-value checks, payment gates, stale-result invalidation, the hosted SSE feed, and saving reviewer feedback. No browser runtime errors were observed. The hosted verification's temporary data was removed; user testing records were preserved.

Razorpay Checkout capture/webhook delivery has not been verified. Configure the provider's test webhook as `https://fraudlens-api-ocjj.onrender.com/v1/webhooks/razorpay` with the matching server webhook secret before expecting captured-payment updates.

## Vercel

Use the existing `fraudlens` project with root directory `frontend`, framework `nextjs`, install command `npm ci`, build command `npm run build`, and automatic output-directory detection. Run the CLI from the repository root so its configured `frontend` root is resolved once.

`.vercelignore` excludes all environment files, backend code/models, training material, caches, and screenshots from the frontend upload. Provide these server-side production environment variables through Vercel's environment store: `FRAUDLENS_API_URL`, `FRAUDLENS_API_KEY`, `FRAUDLENS_ADMIN_TOKEN`, `DEMO_PASSWORD`, `ADMIN_PASSWORD`, `SESSION_SECRET`, and `SITE_URL`. Do not use `NEXT_PUBLIC_` for credentials.

The API proxy allows 90 seconds for an upstream request and has a 120-second platform duration, accommodating the free Render service's cold start. The SSE route has a 300-second platform duration, forwards client cancellation upstream, and the browser reconnects when the stream ends.

## Render

Use a free Python web service, repository `QuantumSenpai/fraudlens`, root directory `backend`, and Python 3.11.18. Build with `pip install -r requirements.txt`; run Uvicorn bound to `0.0.0.0:$PORT` with `--no-proxy-headers`. The service health-check path is `/health` and the model is `xgb_live_v1`.

The CLI-created service uses a Render secret file named `fraudlens.env` and loads it with Uvicorn's `--env-file /etc/secrets/fraudlens.env` option. It contains only backend environment settings. Keep `ENV=dev` and `rzp_test_` keys for this demonstration. The Blueprint alternative in `backend/render.yaml` uses dashboard environment variables instead.

Free Render services can sleep after inactivity, causing a roughly one-minute initial wake-up. This deployment is for demonstration, not production payment processing. Razorpay provider webhooks must separately be configured for the backend's public `/v1/webhooks/razorpay` URL using the matching webhook secret.

## Release verification and rollback

Before release, run the backend tests and frontend lint, type checking, unit tests, build, and dependency audits. Verify the public landing/access routes, both role logins, backend model/database health, an actual low-value check, mandatory high-value review, rejection of an unapproved payment, and the reviewer dashboard over HTTPS. Clean only the isolated release-test records.

Vercel retains prior deployments; use `vercel rollback` to select a known-good deployment. Render retains prior deploys and supports rollback from its deployment history. Do not roll back the additive Supabase migrations or delete application rows to roll back application code.

## Dependency audit triage, 2026-11-16

The frontend production audit reports zero vulnerabilities. The backend audit reports advisories in three older packages; review again by 2026-12-01:

| Package | Affected path | Reachability and disposition |
| --- | --- | --- |
| Starlette 0.38.6 | Form parsing, Windows static-file handling, unrestricted `HTTPEndpoint` methods, URL reconstruction | The API uses JSON models and explicit FastAPI methods, has no upload/form/static-file endpoints, runs on Linux, and does not authorize by reconstructed URL. These advisory paths are not used by this service. A coordinated FastAPI/Starlette upgrade is deferred rather than forcing an unsupported transitive version. |
| python-dotenv 1.0.1 | `set_key`/`unset_key` symlink rewriting | Deployment reads a provider-managed secret file; the server does not call these mutation functions. Defer the library upgrade to dependency maintenance. |
| pytest 8.3.2 | Local temporary test-directory handling | The hosted start command does not run pytest. This is a local test-runner issue, not a public application endpoint. Defer the test-runner upgrade to dependency maintenance. |

No advisory was suppressed and no test was disabled. The audit findings remain visible for maintenance.
