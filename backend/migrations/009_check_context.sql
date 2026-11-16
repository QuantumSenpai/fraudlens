CREATE INDEX IF NOT EXISTS checks_user_created_at_idx ON public.checks (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS checks_device_created_at_idx ON public.checks (device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS payments_failed_created_at_idx ON public.payments (created_at DESC, check_id) WHERE status = 'failed';
CREATE INDEX IF NOT EXISTS transactions_user_timestamp_idx ON public.transactions (user_id, txn_timestamp DESC);

CREATE OR REPLACE FUNCTION public.check_context(
    p_user_id text,
    p_device_id text,
    p_now timestamptz,
    p_user_limit integer,
    p_device_limit integer,
    p_payment_window_minutes integer
) RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
SELECT jsonb_build_object(
    'device', (
        SELECT jsonb_build_object('device_id', device_id, 'first_seen', first_seen, 'timezone', timezone)
        FROM public.devices WHERE device_id = p_device_id
    ),
    'user_checks', coalesce((
        SELECT jsonb_agg(to_jsonb(h) ORDER BY h.created_at DESC)
        FROM (
            SELECT id, device_id, amount, lat, lon, decision, created_at
            FROM public.checks WHERE user_id = p_user_id
            ORDER BY created_at DESC LIMIT least(greatest(p_user_limit, 1), 100)
        ) AS h
    ), '[]'::jsonb),
    'legacy_transactions', coalesce((
        SELECT jsonb_agg(to_jsonb(h) ORDER BY h.txn_timestamp DESC)
        FROM (
            SELECT device_id, amount, lat, lon, txn_timestamp
            FROM public.transactions WHERE user_id = p_user_id
            ORDER BY txn_timestamp DESC LIMIT least(greatest(p_user_limit, 1), 100)
        ) AS h
    ), '[]'::jsonb),
    'device_user_count', (
        SELECT count(*) FROM public.device_users WHERE device_id = p_device_id
    ),
    'device_decisions', coalesce((
        SELECT jsonb_agg(h.decision ORDER BY h.created_at DESC)
        FROM (
            SELECT decision, created_at FROM public.checks
            WHERE device_id = p_device_id
            ORDER BY created_at DESC LIMIT least(greatest(p_device_limit, 1), 100)
        ) AS h
    ), '[]'::jsonb),
    'failed_payment_count', (
        SELECT count(*) FROM public.payments AS p
        JOIN public.checks AS c ON c.id = p.check_id
        WHERE c.user_id = p_user_id AND p.status = 'failed'
          AND p.created_at >= p_now - make_interval(mins => p_payment_window_minutes)
          AND p.created_at <= p_now
    )
);
$$;

REVOKE ALL ON FUNCTION public.check_context(text, text, timestamptz, integer, integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.check_context(text, text, timestamptz, integer, integer, integer) TO service_role;
