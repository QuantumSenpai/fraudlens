# FraudLens control inventory

| Surface | Control | Expected outcome |
|---|---|---|
| All public pages | Brand | Opens landing page |
| All public pages | Header How it works | Opens `/how-it-works` |
| Explore panel | Data use | Opens `/privacy` |
| Explore panel | Reviewer dashboard | Opens admin access or an authorized dashboard |
| All public pages | Header Open demo | Opens merchant access or an authorized demo |
| Mobile header | Explore or Close navigation | Toggles navigation, moves focus inside, traps Tab, closes with Escape |
| Landing | Run a test check, Explore the demo, Open merchant demo | Opens merchant access or demo |
| Landing | Explore the flow | Opens `/how-it-works` |
| Footer | How it works, Merchant demo, Dashboard, Data use | Opens the named route |
| Footer | GitHub | Opens the FraudLens repository in a new tab |
| How it works | Try a check | Opens merchant access or demo |
| Access | Continue | Validates password, starts a signed session, opens the chosen workspace, or shows error |
| Merchant demo | User ID, amount, method | Edits validated check inputs |
| Merchant demo | Add or update optional location | Requests browser location on user action and shows approximate coordinates or a clear error |
| Merchant demo | Remove location | Omits coordinates from future signal and check requests |
| Merchant demo | Run fraud check | Registers signals, sends one check with an idempotency key, displays decision and reasons |
| Merchant result | Continue to test Checkout | Creates one eligible test order and opens Razorpay Checkout |
| Merchant result | Check approval and continue | Asks backend to create an order; pending REVIEW remains blocked by backend |
| Merchant result | Reopen test Checkout | Opens the saved test order without creating another order |
| Merchant result | Refresh capture status | Rechecks the signed Checkout callback; only captured is paid |
| Merchant workspace | How it works, Sign out | Opens guide or clears session |
| Admin | Overview, Reviews, Evaluation | Switches workspace view |
| Admin | Refresh data, Retry | Fetches current view again or shows request error |
| Admin | Reconnect feed | Reopens SSE stream and shows connection state |
| Admin reviews | Pending, Reviewed, All | Filters cases and resets pagination |
| Admin reviews | Previous, Next | Pages by ten cases, disabled at boundaries |
| Admin reviews | Approve, Reject | Opens confirmation for selected case |
| Review dialog | Reviewer, note | Edits resolution details |
| Review dialog | Confirm approve or reject | Saves resolution and feedback label once, then refreshes data |
| Review dialog | Cancel, close, Escape | Closes dialog and restores focus |
| Admin workspace | Sign out | Clears session and returns home |
| Error page | Retry page | Renders the page again |
| Not found | Back home | Opens landing page |

The Chromium fixture suite is `npm run test:browser`. Its results are in `screenshots/browser-results.json`. It uses the existing Next.js session and proxy against an isolated synthetic API; no real Supabase or Razorpay calls are made. See [REFINEMENT.md](REFINEMENT.md) for the environment inventory, screenshots, and exact commands.

Controls and behavior in the visual correction:

| Surface | Control | Expected outcome |
|---|---|---|
| Header | Explore | Opens a composed panel by mouse hover, click, Enter, or Space |
| Explore panel | Product flow, Merchant demo, Reviewer dashboard, Data use | Opens only the real named route; protected destinations redirect to the correct access page |
| Explore panel | Link hover or keyboard focus | Moves one orange row fill and aligned contrast text |
| Explore panel | Escape, close button, backdrop, route change, resize | Closes cleanly; dismissal does not reopen from stale hover; focus returns predictably |
| Mobile Explore | Modal panel | Contains keyboard focus and supports touch selection; uses no hover requirement |
| Decision stage | ALLOW, REVIEW, BLOCK | Changes a labelled illustrative transaction's consequence, reason, and real destination |
| Dashboard | View tabs and review feedback | Preserve information while giving brief transition feedback |
| Access | Merchant / reviewer access switch | Opens the other role's sign-in page |
| Expired workspace | Sign in again | Opens the relevant role's access page |

The final visual correction passed 105 Chromium checks and 17 unit tests. Normal-speed desktop/mobile recordings and raw motion measurements are linked from [REFINEMENT.md](REFINEMENT.md). Unexpected browser console errors and warnings: none.

Remaining live integration checks require locally configured credentials and are unverified. Physical-device testing remains outstanding.
