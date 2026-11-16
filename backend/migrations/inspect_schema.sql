-- Read-only preflight/postflight for the FraudLens public schema.
-- Run in Supabase SQL Editor. Returns catalog metadata only, never application rows or keys.
-- Object presence is not proof of migration history. Compare definitions before skipping/applying SQL.
WITH target_tables(name) AS (
    VALUES ('transactions'), ('merchants'), ('devices'), ('device_users'), ('checks'),
           ('payments'), ('reviews'), ('feedback_labels'), ('razorpay_webhook_events')
), target_functions(name) AS (
    VALUES ('resolve_review'), ('admin_stats'), ('admin_evaluation'),
           ('list_reviews'), ('legacy_stats'), ('check_context')
), tables AS (
    SELECT t.name, c.oid, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS force_rls
    FROM target_tables t
    LEFT JOIN pg_namespace n ON n.nspname = 'public'
    LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = t.name AND c.relkind IN ('r', 'p')
), sections AS (
    SELECT 1 AS sort_order, 'tables_and_rls' AS section,
        coalesce(jsonb_agg(jsonb_build_object(
            'table', name, 'exists', oid IS NOT NULL, 'rls_enabled', rls_enabled,
            'service_role_select', CASE WHEN oid IS NOT NULL THEN has_table_privilege('service_role', oid, 'SELECT') END,
            'service_role_insert', CASE WHEN oid IS NOT NULL THEN has_table_privilege('service_role', oid, 'INSERT') END,
            'service_role_update', CASE WHEN oid IS NOT NULL THEN has_table_privilege('service_role', oid, 'UPDATE') END,
            'service_role_delete', CASE WHEN oid IS NOT NULL THEN has_table_privilege('service_role', oid, 'DELETE') END
        ) ORDER BY name), '[]'::jsonb) AS details FROM tables
    UNION ALL
    SELECT 2, 'columns', coalesce(jsonb_agg(jsonb_build_object(
        'table', table_name, 'column', column_name, 'type', udt_name,
        'nullable', is_nullable, 'default', column_default
    ) ORDER BY table_name, ordinal_position), '[]'::jsonb)
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name IN (SELECT name FROM target_tables)
    UNION ALL
    SELECT 3, 'indexes', coalesce(jsonb_agg(jsonb_build_object(
        'table', tablename, 'index', indexname, 'definition', indexdef
    ) ORDER BY tablename, indexname), '[]'::jsonb)
    FROM pg_indexes WHERE schemaname = 'public' AND tablename IN (SELECT name FROM target_tables)
    UNION ALL
    SELECT 4, 'constraints', coalesce(jsonb_agg(jsonb_build_object(
        'table', t.name, 'constraint', c.conname, 'type', c.contype,
        'validated', c.convalidated, 'definition', pg_get_constraintdef(c.oid)
    ) ORDER BY t.name, c.conname), '[]'::jsonb)
    FROM pg_constraint c JOIN tables t ON t.oid = c.conrelid
    UNION ALL
    SELECT 5, 'functions', coalesce(jsonb_agg(jsonb_build_object(
        'function', p.proname, 'arguments', pg_get_function_identity_arguments(p.oid),
        'definition', pg_get_functiondef(p.oid), 'security_definer', p.prosecdef,
        'service_role_execute', has_function_privilege('service_role', p.oid, 'EXECUTE'),
        'anon_execute', has_function_privilege('anon', p.oid, 'EXECUTE'),
        'authenticated_execute', has_function_privilege('authenticated', p.oid, 'EXECUTE'),
        'public_execute', EXISTS (
            SELECT 1 FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
            WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'
        )
    ) ORDER BY p.proname), '[]'::jsonb)
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname IN (SELECT name FROM target_functions)
    UNION ALL
    SELECT 6, 'policies', coalesce(jsonb_agg(jsonb_build_object(
        'table', tablename, 'policy', policyname, 'roles', roles,
        'command', cmd, 'using', qual, 'with_check', with_check
    ) ORDER BY tablename, policyname), '[]'::jsonb)
    FROM pg_policies WHERE schemaname = 'public' AND tablename IN (SELECT name FROM target_tables)
    UNION ALL
    SELECT 7, 'migration_history_table', jsonb_build_object(
        'exists', to_regclass('supabase_migrations.schema_migrations') IS NOT NULL,
        'note', 'SQL Editor changes may not appear in CLI migration history; inspect schema definitions too.'
    )
)
SELECT section, details FROM sections ORDER BY sort_order;
