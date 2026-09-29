#!/usr/bin/env bash
# Harness de Seguridad + Integración + Pruebas.
# Convierte los FAIL/FALLO reportados por los scripts SQL en un fallo real
# del proceso. Los casos negativos esperados siguen siendo válidos: el script
# SQL los reporta como OK cuando reciben el SQLSTATE esperado.
set -uo pipefail

: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGUSER:=postgres}"
: "${PGDATABASE:=devdb}"

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql no está disponible en PATH." >&2
  exit 127
fi

files=(
  tests/fixtures/01_roles.sql
  tests/fixtures/02_schema.sql
  tests/fixtures/03_security_fixtures.sql
  tests/fixtures/04_grants.sql
  tests/fixtures/06_composite_pk_fixtures.sql
  tests/fixtures/07_ticket_fixtures.sql
  tests/fixtures/08_special_nopk_fixtures.sql
  tests/security/01_matrix.sql
  tests/security/02_invoker_vs_definer.sql
  tests/security/03_negative.sql
  tests/security/04_composite_matrix.sql
  tests/security/05_audit_ownership.sql
  tests/security/06_revoke_public_audit.sql
  tests/security/07_ticket_matrix.sql
  tests/security/08_dynamic_sql_audit.sql
  tests/security/09_special_nopk_matrix.sql
  tests/integration/01_checklist.sql
  tests/integration/02_demo_script.sql
)

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

total=0
failed=0

for file in "${files[@]}"; do
  total=$((total + 1))
  echo
  echo "==> $file"

  if [[ ! -f "$file" ]]; then
    echo "FAIL: archivo no encontrado: $file" >&2
    failed=$((failed + 1))
    continue
  fi

  output="$(psql -X -v ON_ERROR_STOP=1 -f "$file" 2>&1)"
  status=$?
  printf '%s\n' "$output"

  file_failed=0

  if (( status != 0 )); then
    echo "FAIL: psql terminó con código $status en $file" >&2
    file_failed=1
  fi

  # Los scripts existentes expresan aserciones con RAISE NOTICE. Un FAIL/FALLO
  # inesperado debe romper el harness aunque PostgreSQL haya terminado con 0.
  # DYN-04 contiene deliberadamente "FAIL esperado" al detectar su señuelo;
  # esa línea está etiquetada explícitamente como OK-detección y no es un fallo.
  unexpected="$(printf '%s\n' "$output" |
    grep -E 'NOTICE:.*(FAIL|FALLO)(:|[[:space:]])' |
    grep -v 'OK-detección' || true)"

  if [[ -n "$unexpected" ]]; then
    echo "FAIL: aserciones SQL fallidas detectadas en $file:" >&2
    printf '%s\n' "$unexpected" >&2
    file_failed=1
  fi

  if (( file_failed != 0 )); then
    failed=$((failed + 1))
  fi
done

echo
echo "========================================"
echo "Harness: $((total - failed))/$total scripts OK"
echo "========================================"

if (( failed != 0 )); then
  echo "RESULTADO: FAIL ($failed script(s) con errores)" >&2
  exit 1
fi

echo "RESULTADO: PASS"
exit 0
