# Database migrations

Run `001_fraud_gateway.sql`, `003_idempotency_keys.sql`, `004_device_signals.sql`, `005_ml_factors.sql`, `006_razorpay_webhook_events.sql`, `007_admin_functions.sql`, `008_admin_optimization.sql`, `009_check_context.sql`, and `010_function_security.sql` once each in the Supabase SQL Editor. They create the gateway tables, indexes, row-level security settings, idempotency columns, stored device signal fields, explainability output, webhook event deduplication, and database functions for reviews, statistics, and check context. Migration 010 fixes function search paths and restricts client access to the optional RLS event-trigger function. No public or authenticated RLS policies are created.

The backend must use a Supabase secret key (`sb_secret_...`) or legacy service role key from its server environment. Supabase Python SDK 2.16.0 accepts both formats; older 2.7.4 rejects secret keys before making a request. Never put `SUPABASE_KEY` or the service role key in a browser, PWA, browser extension, or other frontend bundle. The service role key bypasses row-level security.

Run `scripts/create_merchant.py` from the repository root to create a demo merchant directly. It displays a random API key once and stores only its lowercase SHA-256 hash. `002_seed_demo_merchant.sql` is an alternative manual seed: replace its placeholder with a 64-character lowercase SHA-256 hash, then run it. Never put the plain API key in SQL or the database.

Checks and payment amounts are stored in INR rupees. Razorpay order amounts will be converted to paise by the API layer.

## Read-only inspection before applying SQL

For an existing project, first run `inspect_schema.sql` in SQL Editor. This helper is not a migration: it reads only catalog metadata for the FraudLens tables, indexes, constraints, functions, privileges, and policies. It does not query transaction rows or merchant API-key hashes. Review the function definitions locally before sharing the output if the project has custom function code.

Do not infer that a whole migration is applied merely because one table or function exists. Compare all objects in each numbered file against the audit. If a migration is partially present, stop and reconcile only the missing or mismatched objects; do not rerun its entire file, delete tables, or reset the database. In particular, migrations 007 and 008 both define `admin_stats`, so inspect the final definition as well as the other functions.

Apply each confirmed pending migration separately, in the documented order, with `BEGIN;` before its contents and `COMMIT;` after. Check its result before continuing. On any error, use `ROLLBACK;`, inspect the cause, and do not continue with later files. Skip 002. Run the audit again after migration and verify every new table has RLS enabled, no policies, the expected constraints/indexes/functions, and service-role privileges. Preserve existing `transactions` policies and rows; report differences instead of automatically removing policies from that legacy table.

macOS zsh, from the repository root, to copy the initial audit:

```zsh
pbcopy < backend/migrations/inspect_schema.sql
```

Paste it into the intended Supabase project's **SQL Editor**, then run it. An audit result is not a successful migration or a live backend integration test.
