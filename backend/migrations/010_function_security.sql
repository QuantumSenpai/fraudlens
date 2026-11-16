-- All application relations are schema-qualified; resolve built-ins only.
ALTER FUNCTION public.resolve_review(uuid, text, text, text) SET search_path = '';
ALTER FUNCTION public.admin_stats() SET search_path = '';
ALTER FUNCTION public.admin_evaluation() SET search_path = '';
ALTER FUNCTION public.list_reviews(text, integer, integer) SET search_path = '';
ALTER FUNCTION public.legacy_stats() SET search_path = '';
ALTER FUNCTION public.check_context(text, text, timestamptz, integer, integer, integer) SET search_path = '';

-- Some projects have this dashboard-created event trigger. It needs no client access.
DO $$
BEGIN
    IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL THEN
        REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
    END IF;
END;
$$;
