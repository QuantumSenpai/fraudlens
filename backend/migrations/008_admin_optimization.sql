CREATE OR REPLACE FUNCTION public.list_reviews(p_status text, p_limit integer, p_offset integer)
RETURNS SETOF jsonb
LANGUAGE sql
STABLE
AS $$
SELECT jsonb_build_object(
    'id', c.id,
    'user_id', c.user_id,
    'device_id', c.device_id,
    'amount', c.amount,
    'currency', c.currency,
    'payment_method', c.payment_method,
    'final_score', c.final_score,
    'ml_score', c.ml_score,
    'rule_score', c.rule_score,
    'triggered_rules', c.triggered_rules,
    'model_version', c.model_version,
    'created_at', c.created_at,
    'review', CASE WHEN r.id IS NULL THEN NULL ELSE jsonb_build_object(
        'check_id', r.check_id,
        'reviewer', r.reviewer,
        'outcome', r.outcome,
        'note', r.note,
        'created_at', r.created_at
    ) END
)
FROM public.checks AS c
LEFT JOIN public.reviews AS r ON r.check_id = c.id
WHERE c.decision = 'REVIEW'
  AND (p_status = 'all' OR (p_status = 'pending' AND r.id IS NULL) OR (p_status = 'reviewed' AND r.id IS NOT NULL))
ORDER BY c.created_at DESC, c.id DESC
LIMIT least(greatest(p_limit, 1), 100)
OFFSET greatest(p_offset, 0);
$$;

REVOKE ALL ON FUNCTION public.list_reviews(text, integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.list_reviews(text, integer, integer) TO service_role;

CREATE OR REPLACE FUNCTION public.legacy_stats()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
WITH totals AS (
    SELECT count(*) AS total, count(*) FILTER (WHERE flagged) AS flagged
    FROM public.transactions
), recent AS (
    SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY t.txn_timestamp DESC), '[]'::jsonb) AS rows
    FROM (
        SELECT * FROM public.transactions ORDER BY txn_timestamp DESC LIMIT 10
    ) AS t
)
SELECT jsonb_build_object(
    'total_transactions', totals.total,
    'flagged_transactions', totals.flagged,
    'flagged_rate_percent', CASE WHEN totals.total = 0 THEN 0 ELSE round(totals.flagged * 100.0 / totals.total, 2) END,
    'recent_transactions', recent.rows
)
FROM totals, recent;
$$;

REVOKE ALL ON FUNCTION public.legacy_stats() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.legacy_stats() TO service_role;

CREATE OR REPLACE FUNCTION public.admin_stats()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
WITH totals AS (
    SELECT
        count(*)::integer AS total_checks,
        count(*) FILTER (WHERE decision = 'ALLOW')::integer AS allow_count,
        count(*) FILTER (WHERE decision = 'REVIEW')::integer AS review_count,
        count(*) FILTER (WHERE decision = 'BLOCK')::integer AS block_count,
        count(*) FILTER (WHERE decision <> 'ALLOW')::integer AS flagged_count,
        round(avg(latency_ms)::numeric, 2) AS average_latency_ms,
        round(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 2) AS p95_scoring_latency_ms
    FROM public.checks
),
top_rules AS (
    SELECT coalesce(
        jsonb_agg(jsonb_build_object('rule', rule_name, 'count', rule_count) ORDER BY rule_count DESC, rule_name),
        '[]'::jsonb
    ) AS value
    FROM (
        SELECT item->>'rule' AS rule_name, count(*)::integer AS rule_count
        FROM public.checks AS c
        CROSS JOIN LATERAL jsonb_array_elements(c.triggered_rules) AS entries(item)
        WHERE item ? 'rule'
        GROUP BY item->>'rule'
        ORDER BY rule_count DESC, rule_name
        LIMIT 10
    ) AS ranked_rules
),
hourly_rows AS (
    SELECT buckets.bucket, count(c.id)::integer AS check_count
    FROM generate_series(
        date_trunc('hour', now()) - interval '23 hours',
        date_trunc('hour', now()),
        interval '1 hour'
    ) AS buckets(bucket)
    LEFT JOIN public.checks AS c
        ON c.created_at >= buckets.bucket
        AND c.created_at < buckets.bucket + interval '1 hour'
    GROUP BY buckets.bucket
),
hourly AS (
    SELECT coalesce(
        jsonb_agg(
            jsonb_build_object(
                'hour', to_char(bucket AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:00:00"Z"'),
                'count', check_count
            ) ORDER BY bucket
        ),
        '[]'::jsonb
    ) AS value
    FROM hourly_rows
)
SELECT jsonb_build_object(
    'total_checks', totals.total_checks,
    'decision_split', jsonb_build_object(
        'ALLOW', totals.allow_count,
        'REVIEW', totals.review_count,
        'BLOCK', totals.block_count
    ),
    'flagged_count', totals.flagged_count,
    'flagged_rate_percent', coalesce(round(100 * totals.flagged_count::numeric / nullif(totals.total_checks, 0), 2), 0),
    'top_triggered_rules', top_rules.value,
    'average_latency_ms', totals.average_latency_ms,
    'p95_scoring_latency_ms', totals.p95_scoring_latency_ms,
    'last_24h_hourly_counts', hourly.value
)
FROM totals, top_rules, hourly;
$$;

REVOKE ALL ON FUNCTION public.admin_stats() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_stats() TO service_role;
