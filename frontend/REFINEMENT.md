# Frontend refinement

The existing Next.js app, session boundary, proxy allowlists, FastAPI endpoints, and test-mode payment flow are retained. A same-origin bug discovered in Chromium was fixed: numeric loopback hosts are compared against the actual Host header because NextURL normalizes them to localhost. Cross-origin hosts, ports, and protocols still fail closed. No second app was created. Existing backend and unrelated working-tree changes were left in place.

## Current visual redesign

The cream-led editorial introduction puts a specific action before a wide charcoal transaction stage: “A decision. Before Checkout.” The CTA is “Run a test check.” The stage shows one explicitly illustrative INR transaction, device context, rules/model evaluation, and three different consequences. REVIEW holds for a reviewer; BLOCK closes the Checkout path; ALLOW explains eligibility for a test order. Each state links to a real route. No request is sent by the illustration.

Explore opens a substantial cream navigation panel beneath the shared header. It contains only product flow, merchant demo, reviewer dashboard, and data use. A single orange row highlight and its clipped dark text move together. The page backdrop dims without blur. Desktop pointer hover and explicit click/keyboard opening are supported; mobile uses a large modal panel. GSAP handles reversible panel choreography, decision state changes, hero hierarchy, and selected section entrances. Dashboard view changes use a short opacity transition without delaying interaction. Reduced motion preserves all controls and content.

The original layered CSS was replaced with shared tokens, public layouts, workspace controls, and explicit breakpoint sections. The retired ledger component and its styles were removed. The existing typefaces, Lucide icons, Next.js primitives, and payment eligibility logic are retained. No environment files or credentials were changed.

Both supplied reference screenshots were available and inspected. The Shade page at https://www.navbar.gallery/navbar/shade was inspected in Chromium. Its gallery provides static desktop/mobile navigation references; FraudLens uses its own composition, copy, assets, and interaction implementation.

Before/after images are retained in `screenshots/before-redesign/` and the current `screenshots/landing-*.png` files. Desktop and mobile interaction videos are in `screenshots/recordings/`.

## Environment inventory

No environment files were edited. Enter values locally, never in chat. None of the frontend variables use `NEXT_PUBLIC_`.

| Location | Name | Secret? | Purpose |
|---|---|---|---|
| `frontend/.env.local` | `FRAUDLENS_API_URL` | No | FastAPI origin, locally `http://127.0.0.1:8000` |
| `frontend/.env.local` | `FRAUDLENS_API_KEY` | Yes | One demo merchant's backend key |
| `frontend/.env.local` | `FRAUDLENS_ADMIN_TOKEN` | Yes | Must match backend `ADMIN_TOKEN` |
| `frontend/.env.local` | `DEMO_PASSWORD` | Yes | Merchant workspace access |
| `frontend/.env.local` | `ADMIN_PASSWORD` | Yes | Reviewer workspace access |
| `frontend/.env.local` | `SESSION_SECRET` | Yes | Session signing secret |
| `frontend/.env.local` | `SITE_URL` | No | Canonical public origin; local `http://localhost:3000` |
| `backend/.env` | `SUPABASE_URL` | No | Database service URL |
| `backend/.env` | `SUPABASE_KEY` | Yes | Server service key |
| `backend/.env` | `RAZORPAY_KEY_ID` | No | Public test key ID |
| `backend/.env` | `RAZORPAY_KEY_SECRET` | Yes | Order and Checkout signing secret |
| `backend/.env` | `RAZORPAY_WEBHOOK_SECRET` | Yes | Webhook verification secret |
| `backend/.env` | `ADMIN_TOKEN` | Yes | Reviewer API authentication |
| `backend/.env` | `ALLOWED_ORIGINS` | No | Explicit origin allowlist |
| `backend/.env` | `TRUSTED_PROXY_IPS` | No | Trusted proxy addresses; deployment dependent |
| `backend/.env` | `ENV` | No | `dev` locally, `prod` on production |
| `backend/.env` | `MODEL_VERSION` | No | Model selector; defaults to compatibility model |

Public/non-secret means the value need not be confidential. It does not mean it belongs in the browser bundle. Only Razorpay's public test `key_id` is passed to Checkout.

## Changed paths in the visual correction

- `frontend/app/page.tsx`, `frontend/app/globals.css`
- `frontend/components/header.tsx`, `frontend/components/decision-stage.tsx`, `frontend/components/page-motion.tsx`, `frontend/components/dashboard.tsx`, `frontend/components/ui/button.tsx`
- Removed unused `frontend/components/lens-visual.tsx`
- `frontend/tests/decision-stage.test.tsx`, `frontend/scripts/verify-browser.mjs`
- `frontend/README.md`, `frontend/REFINEMENT.md`, `frontend/CONTROL-INVENTORY.md`, current screenshots, recordings, and motion measurements

The preceding implementation's changes remain in place. API handlers, credential proxy, payment checks, backend code, and authentication were not changed by this visual correction.

## Static-file audit

The old `frontend/assets/js/*`, `frontend/assets/css/*`, `frontend/index.html`, `frontend/predict.html`, `frontend/dashboard.html`, and `frontend/favicon.ico` were already marked deleted before this work. A source-reference search across frontend, backend, docs, scripts, and the root README found no remaining references to those entrypoints/assets. Next.js routes load from `app`, `components`, `lib`, and `public`. Their existing deletions were preserved; no additional source routes, API handlers, tests, or assets were removed. Retired orbital illustration CSS and the obsolete mobile navigation CSS were removed.

## Verification and screenshots

Final validation passed: lint, typecheck, 17 unit tests across 4 files, 105 Chromium checks, and the production build. The browser suite covers 1440, 1024, 768, 390, and 320px, keyboard focus and dismissal, hover bridge, exact contrast-text alignment, rapid reversal/reopen, touch, resize, reduced motion, sign-out, every menu destination, both reviewer outcomes, synthetic location, delayed API responses, offline recovery, expired sessions, and captured-only payment language. There were no unexpected console warnings, runtime exceptions, or hydration errors. Deliberate offline/request failures are recorded separately in `screenshots/browser-results.json`.

Normal-speed recordings were captured from actual Chromium rendering: [desktop walkthrough](screenshots/recordings/desktop-walkthrough.webm) and [mobile menu and decisions](screenshots/recordings/mobile-menu.webm). These include entrance, menu reveal, moving highlight on desktop, closing, decision changes, scrolling, and the mobile menu. Rendered screenshots and sampled playback frames were inspected, including the open panel and narrow workspace.

In the final recorded sessions, the 95th-percentile requestAnimationFrame interval was 16.8ms on desktop and 16.8ms in the emulated mobile browser. Neither recording reported any long tasks (50ms or longer). Recorded CLS was approximately 0.0000173 desktop and 0 mobile. Raw observations are in `screenshots/motion-desktop.json` and `screenshots/motion-mobile.json`. These measurements include the interaction walkthrough in local headless Chromium with recording enabled. They are not physical-device, production-network, or broad Core Web Vitals results.

The CSS file decreased from roughly 1,450 lines with layered overrides to 859 lines with distinct shared, public, workspace, and breakpoint sections. The before view was dominated by charcoal and a tall two-column ledger. The new view places a compact cream introduction above a horizontal transaction path. On mobile, the CTA precedes a deliberately stacked example with all three processing stages. The desktop menu occupies a substantial cream region, rather than a small navigation hover capsule.

Issues found and fixed during verification: animation starting before the navigation portal mounted; hover reopening immediately after Escape; missing initial keyboard focus placement; misaligned duplicated contrast text due to row borders; missing evaluation step in the narrow demo; full-page screenshot positioning artifacts after a viewport resize. None of those issues remain reproducible in the final suite.

`npm run test` tests browser/API boundaries with synthetic responses. `npm run test:browser` starts the existing Next app with ephemeral fixture-only credentials and an isolated local API on ports 3024 and 3034. It does not read or rewrite environment files. Stop another dev instance before running it because Next owns a development lock. The fixture exercises the actual Next session and proxy routes. Razorpay Checkout is stubbed in the browser; payment verification is synthetic.

Screenshots: [desktop landing](screenshots/landing-1440.png), [1024px landing](screenshots/landing-1024.png), [768px landing](screenshots/landing-768.png), [mobile landing](screenshots/landing-390.png), [desktop merchant](screenshots/merchant-1440.png), [mobile merchant](screenshots/merchant-390.png), [desktop dashboard](screenshots/dashboard-1440.png), [mobile dashboard](screenshots/dashboard-390.png), [navigation highlight](screenshots/navigation-desktop.png). Workspace screenshots contain synthetic fixture data, not live activity. Browser results are recorded in `screenshots/browser-results.json`.

No known blocking UI bugs remain from this pass. Real Supabase persistence, real Razorpay Checkout, and signed provider webhooks remain unverified without live configuration. Browser widths are emulated; physical iOS/Android devices are not tested. Canonical URLs and sitemap URLs are emitted only when `SITE_URL` is configured. Before a public deployment, use the real HTTPS origin and keep the existing production access requirements.

## macOS zsh commands

Install and start the frontend:

```zsh
cd /Users/kyzenn/Projects/fraudlens/frontend
npm ci
[[ -e .env.local ]] || cp .env.example .env.local
open -e .env.local
# Enter configuration locally, then save the file.
npm run dev
```

Run all checks with the dev server stopped:

```zsh
cd /Users/kyzenn/Projects/fraudlens/frontend
npm run lint
npm run typecheck
npm run test
npm run build
npx playwright install chromium
npm run test:browser
```

The browser test optionally accepts `CHROMIUM_EXECUTABLE=/absolute/path/to/chromium` when using an existing Chromium installation. This is a test-runner option, not an application environment requirement.

Run the existing backend in a separate zsh terminal after configuring `backend/.env` and applying the documented database migrations:

```zsh
cd /Users/kyzenn/Projects/fraudlens
python3.11 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
[[ -e backend/.env ]] || cp backend/.env.example backend/.env
open -e backend/.env
cd backend
.venv/bin/python -m uvicorn main:app --reload --port 8000 --no-proxy-headers
```
