-- tests/security/10_generated_routine_discovery.sql
-- Discovery genérico de procedures. No asume la API final de Joyce.
\set ON_ERROR_STOP on

SELECT
  n.nspname AS schema_name,
  p.proname AS routine_name,
  p.oid::regprocedure::text AS identity_signature,
  r.rolname AS owner,
  CASE WHEN p.prosecdef THEN 'DEFINER' ELSE 'INVOKER' END AS security,
  COALESCE(
    (SELECT string_agg(cfg, ' | ' ORDER BY cfg)
     FROM unnest(p.proconfig) AS c(cfg)
     WHERE cfg LIKE 'search_path=%'),
    '(session/default)'
  ) AS search_path,
  pg_get_function_identity_arguments(p.oid) AS identity_arguments,
  pg_get_function_result(p.oid) AS return_type,
  has_function_privilege('public', p.oid, 'EXECUTE') AS public_execute
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
JOIN pg_roles r ON r.oid = p.proowner
WHERE n.nspname = COALESCE(NULLIF(current_setting('crudgen.discovery_schema', true), ''), 'lab')
  AND p.prokind = 'p'
  AND p.proname LIKE COALESCE(current_setting('crudgen.discovery_prefix', true), '') || '%'
ORDER BY p.proname, p.oid;

SELECT
  count(*) AS discovered_procedures,
  count(*) FILTER (WHERE p.prosecdef) AS security_definer,
  count(*) FILTER (WHERE NOT p.prosecdef) AS security_invoker,
  count(*) FILTER (WHERE has_function_privilege('public', p.oid, 'EXECUTE')) AS public_execute_leaks
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = COALESCE(NULLIF(current_setting('crudgen.discovery_schema', true), ''), 'lab')
  AND p.prokind = 'p'
  AND p.proname LIKE COALESCE(current_setting('crudgen.discovery_prefix', true), '') || '%';
