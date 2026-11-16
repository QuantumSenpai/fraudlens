CREATE OR REPLACE FUNCTION public.resolve_review(
    p_check_id uuid,
    p_reviewer text,
    p_outcome text,
    p_note text
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    check_decision text;
    feedback_label text;
BEGIN
    SELECT decision INTO check_decision
    FROM public.checks
    WHERE id = p_check_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'check_not_found';
    END IF;

    IF check_decision <> 'REVIEW' THEN
        RAISE EXCEPTION 'check_not_reviewable';
    END IF;

    IF p_outcome NOT IN ('approve', 'reject') THEN
        RAISE EXCEPTION 'invalid_review_outcome';
    END IF;

    feedback_label := CASE WHEN p_outcome = 'reject' THEN 'fraud' ELSE 'legit' END;

    INSERT INTO public.reviews (check_id, reviewer, outcome, note)
    VALUES (p_check_id, p_reviewer, p_outcome, p_note);

    INSERT INTO public.feedback_labels (check_id, label, source)
    VALUES (p_check_id, feedback_label, 'reviewer')
    ON CONFLICT (check_id) DO UPDATE
    SET label = EXCLUDED.label, source = EXCLUDED.source, created_at = now();

    RETURN jsonb_build_object(
        'check_id', p_check_id,
        'reviewer', p_reviewer,
        'outcome', p_outcome,
        'label', feedback_label,
        'note', p_note
    );
END;
$$;

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

CREATE OR REPLACE FUNCTION public.admin_evaluation()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
WITH matrix AS (
    SELECT
        count(*) FILTER (WHERE l.label = 'fraud' AND c.decision IN ('REVIEW', 'BLOCK'))::integer AS true_positive,
        count(*) FILTER (WHERE l.label = 'legit' AND c.decision IN ('REVIEW', 'BLOCK'))::integer AS false_positive,
        count(*) FILTER (WHERE l.label = 'fraud' AND c.decision = 'ALLOW')::integer AS false_negative,
        count(*) FILTER (WHERE l.label = 'legit' AND c.decision = 'ALLOW')::integer AS true_negative,
        count(*)::integer AS labels_total
    FROM public.feedback_labels AS l
    JOIN public.checks AS c ON c.id = l.check_id
)
SELECT jsonb_build_object(
    'labels_total', labels_total,
    'true_positive', true_positive,
    'false_positive', false_positive,
    'false_negative', false_negative,
    'true_negative', true_negative,
    'precision', round(true_positive::numeric / nullif(true_positive + false_positive, 0), 4),
    'recall', round(true_positive::numeric / nullif(true_positive + false_negative, 0), 4),
    'false_positive_rate', round(false_positive::numeric / nullif(false_positive + true_negative, 0), 4)
)
FROM matrix;
$$;

REVOKE ALL ON FUNCTION public.resolve_review(uuid, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.admin_stats() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.admin_evaluation() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_review(uuid, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.admin_stats() TO service_role;
GRANT EXECUTE ON FUNCTION public.admin_evaluation() TO service_role;
