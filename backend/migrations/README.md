# Database migrations

Run `001_fraud_gateway.sql`, `003_idempotency_keys.sql`, `004_device_signals.sql`, `005_ml_factors.sql`, `006_razorpay_webhook_events.sql`, `007_admin_functions.sql`, `008_admin_optimization.sql`, and `009_check_context.sql` once each in the Supabase SQL Editor. They create the gateway tables, indexes, row-level security settings, idempotency columns, stored device signal fields, explainability output, webhook event deduplication, and database functions for reviews, statistics, and check context. No public or authenticated RLS policies are created.

The backend must use the Supabase service role key from its server environment. Never put `SUPABASE_KEY` or the service role key in a browser, PWA, browser extension, or other frontend bundle. The service role key bypasses row-level security.

Run `scripts/create_merchant.py` from the repository root to create a demo merchant directly. It displays a random API key once and stores only its lowercase SHA-256 hash. `002_seed_demo_merchant.sql` is an alternative manual seed: replace its placeholder with a 64-character lowercase SHA-256 hash, then run it. Never put the plain API key in SQL or the database.

Checks and payment amounts are stored in INR rupees. Razorpay order amounts will be converted to paise by the API layer.
